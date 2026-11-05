import express, { Request, Response } from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import fs from 'fs';
import { execFile } from 'child_process';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;
const HOST = '0.0.0.0';

// Allow up to 50MB for PDF base64 payloads
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Ensure upload directories exist
const UPLOADS_DIR = path.resolve(__dirname, 'data/uploads');
const TEMP_DIR = path.resolve(__dirname, 'data/uploads/temp');
fs.mkdirSync(UPLOADS_DIR, { recursive: true });
fs.mkdirSync(TEMP_DIR, { recursive: true });

// Helper to execute Python DB CLI commands
function runDbCli(args: string[]): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    execFile(pythonCmd, ['-m', 'app.db.cli', ...args], { cwd: __dirname }, (error, stdout, stderr) => {
      if (error) {
        console.error(`[DB CLI Error] command args: ${args.join(' ')}:`, stderr || error.message);
        return reject(new Error(stderr || error.message));
      }
      try {
        // Find last valid JSON in stdout in case any warnings were printed
        const lines = stdout.trim().split('\n');
        let parsed = null;
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (line.startsWith('{') || line.startsWith('[')) {
            try {
              parsed = JSON.parse(line);
              break;
            } catch {
              // continue searching upwards
            }
          }
        }
        if (parsed !== null) {
          resolve(parsed);
        } else {
          // Try parsing entire stdout
          resolve(JSON.parse(stdout.trim()));
        }
      } catch (err: any) {
        console.error(`[DB CLI JSON Parse Error] stdout was:`, stdout);
        reject(new Error(`Failed to parse CLI output: ${err.message}`));
      }
    });
  });
}

// Initialize SQLite database on server startup
runDbCli(['init'])
  .then(() => console.log('[SQLite DB] Verified SQLite schema and reference PR initialization.'))
  .catch(err => console.error('[SQLite DB Init Error]', err));

// 1. API: Dashboard Summary (Aggregated statistics from SQLite)
app.get('/api/dashboard/summary', async (_req: Request, res: Response) => {
  try {
    const summary = await runDbCli(['summary']);
    res.json(summary);
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to retrieve dashboard summary: ' + err.message });
  }
});

// 2. API: List Verifications (With search, filter, and pagination)
app.get('/api/verifications', async (req: Request, res: Response) => {
  try {
    const search = (req.query.search as string) || 'null';
    const decision = (req.query.decision as string) || 'null';
    const limit = (req.query.limit as string) || '50';
    const offset = (req.query.offset as string) || '0';

    const result = await runDbCli(['list', search, decision, limit, offset]);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to list verifications: ' + err.message });
  }
});

// 3. API: Get Single Verification Details
app.get('/api/verifications/:id', async (req: Request, res: Response) => {
  try {
    const id = req.params.id;
    const result = await runDbCli(['get', id]);
    if (result.error) {
      return res.status(404).json(result);
    }
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to retrieve verification: ' + err.message });
  }
});

// 3b. API: Get Verification Results Only
app.get('/api/verifications/:id/results', async (req: Request, res: Response) => {
  try {
    const id = req.params.id;
    const result = await runDbCli(['get', id]);
    if (result.error) {
      return res.status(404).json(result);
    }
    res.json({
      verification_id: result.id,
      supplier_id: result.supplier_id,
      supplier_name: result.supplier_name,
      overall_decision: result.overall_decision,
      machine_decision: result.machine_decision || result.overall_decision,
      human_review_decision: result.human_review_decision ?? null,
      effective_decision: result.effective_decision || result.overall_decision,
      triggered_rule_ids: result.triggered_rule_ids || [],
      validation_results: result.validation_results || [],
      comparison_results: result.comparison_results || []
    });
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to retrieve verification results: ' + err.message });
  }
});

// 3c. API: Get Verification Documents Metadata
app.get('/api/verifications/:id/documents', async (req: Request, res: Response) => {
  try {
    const id = req.params.id;
    const result = await runDbCli(['get', id]);
    if (result.error) {
      return res.status(404).json(result);
    }
    res.json({
      verification_id: result.id,
      documents: result.documents || []
    });
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to retrieve verification documents: ' + err.message });
  }
});

// 3d. API: Stream the original uploaded PDF for a verification.
// Uses the persisted document record, so <uuid>_combined.pdf names work even
// though the UI shows the supplier's original filename.
app.get('/api/verifications/:id/document', async (req: Request, res: Response) => {
  try {
    const result = await runDbCli(['get', req.params.id]);
    if (result.error) {
      return res.status(404).json(result);
    }

    const document = (result.documents && result.documents[0]) || result.document || null;
    if (!document) {
      return res.status(404).json({ error: 'No document is attached to this verification.' });
    }

    const candidates = [
      document.file_path,
      document.file_path ? path.resolve(UPLOADS_DIR, path.basename(document.file_path)) : null,
      document.original_filename ? path.resolve(UPLOADS_DIR, path.basename(document.original_filename)) : null,
      document.original_filename ? path.resolve(__dirname, 'data/input', path.basename(document.original_filename)) : null,
    ].filter((candidate): candidate is string => Boolean(candidate));

    const found = candidates.find(candidate => fs.existsSync(candidate));
    if (!found) {
      return res.status(404).json({ error: 'Source document file is missing from storage.' });
    }

    const downloadName = path.basename(document.original_filename || 'supplier_document.pdf');
    res.setHeader('Content-Type', document.mime_type || 'application/pdf');
    res.setHeader('Content-Disposition', `inline; filename="${downloadName.replace(/"/g, '')}"`);
    return res.sendFile(path.resolve(found));
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to retrieve source document: ' + err.message });
  }
});

// 4. API: Upload and Verify Supplier Document (Single Combined PDF: Quotation + Terms & Conditions)
app.post(['/api/documents/upload', '/api/verifications'], async (req: Request, res: Response) => {
  try {
    const {
      supplier_id,
      supplier_name,
      document_base64,
      document_filename,
      quotation_base64,
      quotation_filename,
      contract_base64,
      contract_filename
    } = req.body;

    const base64Data = document_base64 || quotation_base64;
    const docName = document_filename || quotation_filename || 'combined_supplier_document.pdf';

    if (!base64Data && !contract_base64) {
      return res.status(400).json({
        error: 'Please upload the combined supplier document PDF (containing quotation and terms & conditions) to proceed.'
      });
    }

    const uniquePrefix = `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const effectiveSupplierId = supplier_id ? supplier_id.trim() : 'null';
    const effectiveSupplierName = supplier_name ? supplier_name.trim() : 'null';

    // If legacy two-file payload was provided, pass both to be merged by CLI service
    if (quotation_base64 && contract_base64) {
      const qTempPath = path.join(TEMP_DIR, `${uniquePrefix}_quotation.pdf`);
      const cTempPath = path.join(TEMP_DIR, `${uniquePrefix}_contract.pdf`);
      fs.writeFileSync(qTempPath, Buffer.from(quotation_base64, 'base64'));
      fs.writeFileSync(cTempPath, Buffer.from(contract_base64, 'base64'));

      const cliOutput = await runDbCli([
        'verify',
        qTempPath,
        cTempPath,
        effectiveSupplierId,
        effectiveSupplierName,
        quotation_filename || 'quotation.pdf'
      ]);

      try {
        if (fs.existsSync(qTempPath)) fs.unlinkSync(qTempPath);
        if (fs.existsSync(cTempPath)) fs.unlinkSync(cTempPath);
      } catch {}

      if (cliOutput.error) {
        return res.status(500).json({ error: 'Verification failed: ' + cliOutput.error });
      }

      return res.json({
        success: true,
        message: 'Combined supplier document verification completed successfully',
        result: cliOutput.result
      });
    }

    // Standard single combined PDF upload
    const cleanFilename = path.basename(docName);
    const docTempPath = path.join(TEMP_DIR, `${uniquePrefix}_${cleanFilename}`);
    fs.writeFileSync(docTempPath, Buffer.from(base64Data, 'base64'));

    const cliOutput = await runDbCli([
      'verify',
      docTempPath,
      effectiveSupplierId,
      effectiveSupplierName,
      cleanFilename
    ]);

    try {
      if (fs.existsSync(docTempPath)) fs.unlinkSync(docTempPath);
    } catch {}

    if (cliOutput.error) {
      return res.status(500).json({ error: 'Verification failed: ' + cliOutput.error });
    }

    res.json({
      success: true,
      message: 'Combined supplier document verification completed successfully',
      result: cliOutput.result
    });
  } catch (err: any) {
    console.error('Error running verification upload:', err);
    res.status(500).json({ error: 'Verification execution failed: ' + err.message });
  }
});

// 5. API: Human Reviews (Pending cases list)
app.get('/api/reviews', async (_req: Request, res: Response) => {
  try {
    const reviews = await runDbCli(['reviews']);
    res.json(reviews);
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to retrieve human reviews: ' + err.message });
  }
});

// 5b. API: Submit Human Review Decision
app.post(['/api/reviews/:id/decision', '/api/human-review'], async (req: Request, res: Response) => {
  try {
    const verificationId = req.params.id || req.body.supplier_id || req.body.verification_id;
    const { reviewer_name, reviewer_role, review_decision, comments, dispensation_reason } = req.body;

    if (!verificationId || !reviewer_name || !review_decision) {
      return res.status(400).json({ error: 'Missing required review fields (verification ID, reviewer name, decision).' });
    }

    const result = await runDbCli([
      'review',
      verificationId,
      reviewer_name,
      reviewer_role || 'Procurement Auditor',
      review_decision,
      comments || '',
      dispensation_reason || ''
    ]);

    if (result.error) {
      return res.status(400).json(result);
    }

    res.json({ success: true, review: result });
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to record human review: ' + err.message });
  }
});

// 6. API: Reference Purchase Request (From SQLite)
app.get('/api/purchase-request', async (_req: Request, res: Response) => {
  try {
    const pr = await runDbCli(['pr']);
    if (!pr || pr.error) {
      return res.status(404).json({ error: 'Purchase request not found in database' });
    }
    res.json(pr);
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to load purchase request: ' + err.message });
  }
});

// 7. API: Database Reset (Resets verifications and reviews to clean zero state)
app.post('/api/admin/reset', async (_req: Request, res: Response) => {
  try {
    const result = await runDbCli(['reset']);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to reset database: ' + err.message });
  }
});

// 8. API: Raw PDF File Preview (Safely served from uploads or input directory)
app.get('/api/raw-document/:filename', (req: Request, res: Response) => {
  const filename = path.basename(req.params.filename); // Sanitize filename
  
  // First check in uploads directory
  const uploadPath = path.resolve(UPLOADS_DIR, filename);
  if (fs.existsSync(uploadPath)) {
    res.setHeader('Content-Type', 'application/pdf');
    return res.sendFile(uploadPath);
  }

  // Fallback check in input directory
  const inputPath = path.resolve(__dirname, 'data/input', filename);
  if (fs.existsSync(inputPath)) {
    res.setHeader('Content-Type', 'application/pdf');
    return res.sendFile(inputPath);
  }

  res.status(404).send('Document not found');
});

// 9. API: Individual Report PDF Download
app.get('/api/download/individual-pdf', (req: Request, res: Response) => {
  const supplierId = req.query.supplier_id as string;
  if (!supplierId) {
    return res.status(400).json({ error: 'Missing supplier_id query parameter' });
  }

  const safeId = path.basename(supplierId.toLowerCase());
  const reportPath = path.resolve(__dirname, `outputs/reports/individual/${safeId}_verification_report.pdf`);
  if (fs.existsSync(reportPath)) {
    return res.download(reportPath, `${supplierId}_verification_report.pdf`);
  }

  res.status(404).json({ error: 'Report not found for this supplier' });
});

// Mount Vite in development or static build in production
async function startServer() {
  const isProd = process.env.NODE_ENV === 'production';

  if (!isProd) {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (_req: Request, res: Response) => {
      res.sendFile(path.resolve(__dirname, 'dist/index.html'));
    });
  }

  app.listen(PORT, HOST, () => {
    console.log(`[Supplier Verification Platform] Server listening on http://${HOST}:${PORT}`);
  });
}

startServer();
