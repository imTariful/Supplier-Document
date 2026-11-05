import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  UploadCloud,
  History,
  UserCheck,
  Settings,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  Download,
  AlertCircle,
  XCircle,
  CheckCircle2,
  Clock,
  ArrowLeft,
  Menu,
  X,
  RefreshCw,
  FileText,
  Building,
  RotateCcw,
  ExternalLink,
  Trash2
} from 'lucide-react';

// --- Interfaces matching SQLite Database Schema ---

interface PRItem {
  pr_number: string;
  item_code: string;
  item_description: string;
  specification: string;
  quantity: number;
  unit: string;
  max_unit_price: number;
  target_delivery_days: number;
  required_vat_rate: number;
  max_advance_pct: number;
}

interface PRResponse {
  pr_number: string;
  company: string;
  department: string;
  date: string;
  currency: string;
  items: PRItem[];
}

interface HumanReviewData {
  reviewer_name: string;
  reviewer_role: string;
  review_decision: string;
  comments: string;
  dispensation_reason: string;
  reviewed_at: string;
}

interface VerificationSummaryItem {
  id: string;
  supplier_id: string;
  supplier_name: string;
  purchase_request_id: string;
  overall_decision: 'APPROVED' | 'REJECTED' | 'NEEDS_HUMAN_REVIEW';
  machine_decision?: 'APPROVED' | 'REJECTED' | 'NEEDS_HUMAN_REVIEW';
  human_review_decision?: string | null;
  effective_decision?: 'APPROVED' | 'REJECTED' | 'NEEDS_HUMAN_REVIEW';
  processing_status: string;
  submission_timestamp: string;
  completion_timestamp: string | null;
  passed_checks_count: number;
  failed_checks_count: number;
  review_checks_count: number;
  triggered_rule_ids: string[];
  documents_count: number;
  has_human_review: boolean;
  human_review?: HumanReviewData | null;
}

interface DashboardSummary {
  total_verifications: number;
  approved: number;
  rejected: number;
  needs_human_review: number;
  recent_verifications: VerificationSummaryItem[];
}

interface DocumentMetadata {
  id: string;
  verification_id: string;
  original_filename: string;
  document_type: string;
  file_path: string;
  mime_type: string;
  file_size: number;
  page_count: number;
  upload_timestamp: string;
  extraction_status: string;
}

interface ValidationResultRecord {
  id: string;
  verification_id: string;
  rule_id: string;
  rule_name: string;
  result: 'PASS' | 'FAIL' | 'REVIEW' | 'NOT_EVALUABLE';
  severity: 'REJECT' | 'HUMAN_REVIEW' | 'INFO';
  actual_value: string;
  expected_value: string;
  document: string;
  page: number;
  evidence_text: string;
  explanation: string;
}

interface ComparisonResultRecord {
  item_code: string;
  item_description: string;
  specification?: string;
  requested_qty: number;
  quoted_qty: number;
  unit: string;
  qty_deviation_pct: number;
  max_unit_price: number;
  quoted_unit_price: number;
  price_deviation_pct: number;
}

interface ExtractedQuotationLineItem {
  item_code: string;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  line_total: number;
  source_text?: string;
  page_number?: number;
}

interface ExtractedQuotationSection {
  supplier_name?: string;
  quotation_no?: string;
  pr_reference?: string;
  date_str?: string;
  tin?: string;
  bin?: string;
  validity_days?: number;
  delivery_days?: number;
  advance_pct?: number;
  remaining_days?: number;
  items?: ExtractedQuotationLineItem[];
  subtotal?: number;
  vat_amount?: number;
  vat_separate?: boolean;
  grand_total?: number;
  page_count?: number;
  source_filename?: string;
}

interface ExtractedContractSection {
  agreement_no?: string;
  supplier_name?: string;
  pr_reference?: string;
  tin?: string;
  bin?: string;
  delivery_days?: number;
  advance_pct?: number;
  remaining_days?: number;
  penalty_clause?: string;
  penalty_rate_pct?: number;
  penalty_basis?: string;
  vat_separate?: boolean;
  page_count?: number;
  source_filename?: string;
}

interface VerificationDetailRecord extends VerificationSummaryItem {
  verification_notes: string;
  comparison_results: ComparisonResultRecord[];
  documents: DocumentMetadata[];
  validation_results: ValidationResultRecord[];
  human_reviews: HumanReviewData[];
  latest_human_review?: HumanReviewData | null;
  error_message?: string | null;
  quotation_details?: ExtractedQuotationSection | null;
  contract_terms?: ExtractedContractSection | null;
}

interface PendingReviewCase {
  id: string;
  supplier_id: string;
  supplier_name: string;
  submission_timestamp: string;
  review_checks_count: number;
  failed_checks_count: number;
  verification_notes: string;
  flagged_issues: {
    rule_id: string;
    rule_name: string;
    result: string;
    severity: string;
    evidence_text: string;
    explanation: string;
    document: string;
    page: number;
  }[];
  has_review: boolean;
  latest_review?: HumanReviewData | null;
}

function effectiveDecision(record: { effective_decision?: string; overall_decision: string }): string {
  return record.effective_decision || record.overall_decision;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'upload' | 'history' | 'review' | 'settings'>('dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Core Data States loaded from SQLite
  const [summary, setSummary] = useState<DashboardSummary>({
    total_verifications: 0,
    approved: 0,
    rejected: 0,
    needs_human_review: 0,
    recent_verifications: []
  });
  const [verificationsList, setVerificationsList] = useState<VerificationSummaryItem[]>([]);
  const [pendingReviews, setPendingReviews] = useState<PendingReviewCase[]>([]);
  const [prData, setPrData] = useState<PRResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Selected Verification for Detailed View
  const [selectedVerification, setSelectedVerification] = useState<VerificationDetailRecord | null>(null);
  const [expandedRuleRows, setExpandedRuleRows] = useState<Record<string, boolean>>({});

  // History search and filter
  const [historySearch, setHistorySearch] = useState<string>('');
  const [historyFilter, setHistoryFilter] = useState<string>('ALL');

  // Upload Form State for Single Combined Document
  const [uploadSupplierId, setUploadSupplierId] = useState<string>('');
  const [uploadSupplierName, setUploadSupplierName] = useState<string>('');
  const [selectedPrId, setSelectedPrId] = useState<string>('PR-2026-114');
  const [supplierDocFile, setSupplierDocFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [uploadLoading, setUploadLoading] = useState<boolean>(false);
  const [uploadStatusMsg, setUploadStatusMsg] = useState<string>('');
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Human Review Form State
  const [selectedReviewCaseId, setSelectedReviewCaseId] = useState<string>('');
  const [reviewerName, setReviewerName] = useState<string>('');
  const [reviewerRole, setReviewerRole] = useState<string>('Procurement Auditor');
  const [reviewDecision, setReviewDecision] = useState<string>('APPROVED_WITH_DISPENSATION');
  const [reviewComments, setReviewComments] = useState<string>('');
  const [reviewDispensationReason, setReviewDispensationReason] = useState<string>('');
  const [reviewSubmitting, setReviewSubmitting] = useState<boolean>(false);
  const [reviewSuccessMsg, setReviewSuccessMsg] = useState<string | null>(null);

  // Reset database state
  const [resettingDb, setResettingDb] = useState<boolean>(false);
  const [resetConfirmOpen, setResetConfirmOpen] = useState<boolean>(false);

  // Fetch summary and list from SQLite
  const refreshAllData = async () => {
    try {
      const [sumRes, verifRes, revRes, prRes] = await Promise.all([
        fetch('/api/dashboard/summary').then(r => r.json()),
        fetch('/api/verifications').then(r => r.json()),
        fetch('/api/reviews').then(r => r.json()),
        fetch('/api/purchase-request').then(r => r.json())
      ]);

      if (sumRes && !sumRes.error) {
        setSummary(sumRes);
      }
      if (verifRes && verifRes.verifications) {
        setVerificationsList(verifRes.verifications);
      }
      if (revRes && revRes.reviews) {
        setPendingReviews(revRes.reviews);
        if (revRes.reviews.length > 0 && !selectedReviewCaseId) {
          setSelectedReviewCaseId(revRes.reviews[0].id);
        }
      }
      if (prRes && !prRes.error) {
        setPrData(prRes);
      }
    } catch (err) {
      console.error('Failed to load database records:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAllData();
  }, []);

  // Fetch single verification details
  const viewVerificationDetails = async (id: string) => {
    try {
      setLoading(true);
      const res = await fetch(`/api/verifications/${id}`).then(r => r.json());
      if (res && !res.error) {
        setSelectedVerification(res);
        setExpandedRuleRows({});
      }
    } catch (err) {
      console.error('Failed to retrieve verification details:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle Document Upload & Verification (Single Combined PDF: Quotation + Terms & Conditions)
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplierDocFile) {
      setUploadError('Please select or drop a combined supplier document (PDF) containing both quotation and terms & conditions.');
      return;
    }

    if (!supplierDocFile.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Invalid file format. Please upload a PDF document (.pdf).');
      return;
    }

    if (supplierDocFile.size > 50 * 1024 * 1024) {
      setUploadError('File size exceeds the 50MB maximum limit.');
      return;
    }

    setUploadLoading(true);
    setUploadError(null);
    setUploadStatusMsg('Reading and encoding combined supplier document...');

    try {
      const toBase64 = (file: File) => new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
          const res = reader.result as string;
          resolve(res.split(',')[1]);
        };
        reader.onerror = error => reject(error);
      });

      const docBase64 = await toBase64(supplierDocFile);

      setUploadStatusMsg('Executing LangGraph verification workflow & evaluating business rules across document sections...');

      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplier_id: uploadSupplierId.trim() || undefined,
          supplier_name: uploadSupplierName.trim() || undefined,
          document_base64: docBase64,
          document_filename: supplierDocFile.name
        })
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Verification processing failed.');
      }

      setUploadStatusMsg('Verification completed and saved to SQLite.');
      await refreshAllData();

      // Clear upload inputs
      setSupplierDocFile(null);
      setUploadSupplierId('');
      setUploadSupplierName('');

      // Directly open the result
      if (data.result) {
        setSelectedVerification(data.result);
      }
    } catch (err: any) {
      setUploadError(err.message || 'An error occurred during verification.');
    } finally {
      setUploadLoading(false);
    }
  };

  // Submit human auditor review
  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReviewCaseId) return;
    if (!reviewerName.trim()) {
      alert('Please enter your name as the reviewing auditor.');
      return;
    }

    setReviewSubmitting(true);
    setReviewSuccessMsg(null);

    try {
      const res = await fetch(`/api/reviews/${selectedReviewCaseId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_name: reviewerName.trim(),
          reviewer_role: reviewerRole.trim(),
          review_decision: reviewDecision,
          comments: reviewComments.trim(),
          dispensation_reason: reviewDispensationReason.trim()
        })
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Failed to submit review.');
      }

      setReviewSuccessMsg(`Review successfully recorded as ${reviewDecision.replace(/_/g, ' ')}.`);
      setReviewComments('');
      setReviewDispensationReason('');
      await refreshAllData();
    } catch (err: any) {
      alert(err.message || 'Error recording review.');
    } finally {
      setReviewSubmitting(false);
    }
  };

  // Handle resetting the database
  const handleResetDatabase = async () => {
    setResettingDb(true);
    try {
      const res = await fetch('/api/admin/reset', { method: 'POST' }).then(r => r.json());
      if (res.success) {
        setSelectedVerification(null);
        setSelectedReviewCaseId('');
        await refreshAllData();
        setResetConfirmOpen(false);
      } else {
        alert(res.error || 'Failed to reset database.');
      }
    } catch (err: any) {
      alert('Reset failed: ' + err.message);
    } finally {
      setResettingDb(false);
    }
  };

  // Filter verification history
  const filteredVerifications = verificationsList.filter(item => {
    const matchSearch =
      historySearch === '' ||
      item.supplier_name.toLowerCase().includes(historySearch.toLowerCase()) ||
      item.supplier_id.toLowerCase().includes(historySearch.toLowerCase());

    const matchDecision =
      historyFilter === 'ALL' ||
      effectiveDecision(item) === historyFilter;

    return matchSearch && matchDecision;
  });

  const activeReviewCase = pendingReviews.find(r => r.id === selectedReviewCaseId);

  return (
    <div className="flex h-screen bg-gray-50 text-slate-800 font-sans antialiased overflow-hidden">
      {/* Sidebar Navigation */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-60 bg-white border-r border-gray-200 transform transition-transform duration-150 ease-in-out md:translate-x-0 md:static ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Brand Header */}
          <div className="px-5 py-4 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <Building className="w-5 h-5 text-blue-600" />
              <div>
                <h1 className="text-sm font-bold text-slate-900 leading-tight">Aamar Garments</h1>
                <p className="text-xs text-gray-700">Document Verification</p>
              </div>
            </div>
          </div>

          {/* Nav Items */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            <button
              onClick={() => {
                setActiveTab('dashboard');
                setSelectedVerification(null);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'dashboard' && !selectedVerification
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-slate-700 hover:bg-gray-100 hover:text-slate-900'
              }`}
            >
              <LayoutDashboard className="w-4 h-4 mr-3 text-gray-500" />
              Dashboard
            </button>

            <button
              onClick={() => {
                setActiveTab('upload');
                setSelectedVerification(null);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'upload' && !selectedVerification
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-slate-700 hover:bg-gray-100 hover:text-slate-900'
              }`}
            >
              <UploadCloud className="w-4 h-4 mr-3 text-gray-500" />
              Upload Documents
            </button>

            <button
              onClick={() => {
                setActiveTab('history');
                setSelectedVerification(null);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'history' && !selectedVerification
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-slate-700 hover:bg-gray-100 hover:text-slate-900'
              }`}
            >
              <div className="flex items-center">
                <History className="w-4 h-4 mr-3 text-gray-500" />
                Verification History
              </div>
              {verificationsList.length > 0 && (
                <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                  {verificationsList.length}
                </span>
              )}
            </button>

            <button
              onClick={() => {
                setActiveTab('review');
                setSelectedVerification(null);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'review' && !selectedVerification
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-slate-700 hover:bg-gray-100 hover:text-slate-900'
              }`}
            >
              <div className="flex items-center">
                <UserCheck className="w-4 h-4 mr-3 text-gray-500" />
                Human Review
              </div>
              {pendingReviews.length > 0 && (
                <span className="text-xs bg-amber-100 text-amber-800 font-semibold px-1.5 py-0.5 rounded">
                  {pendingReviews.length}
                </span>
              )}
            </button>

            <button
              onClick={() => {
                setActiveTab('settings');
                setSelectedVerification(null);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'settings' && !selectedVerification
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-slate-700 hover:bg-gray-100 hover:text-slate-900'
              }`}
            >
              <Settings className="w-4 h-4 mr-3 text-gray-500" />
              Settings
            </button>
          </nav>

          {/* Database Footer Status */}
          <div className="p-3 border-t border-gray-200 bg-gray-50">
            <div className="text-xs text-gray-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Database:</span>
                <span className="font-medium text-slate-700">SQLite</span>
              </div>
              <div className="flex items-center justify-between">
                <span>ORM:</span>
                <span className="font-medium text-slate-700">SQLAlchemy</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Status:</span>
                <span className="inline-flex items-center text-emerald-600 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></span>
                  Connected
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1 text-gray-600 hover:text-gray-900"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {selectedVerification ? (
              <div className="flex items-center space-x-2 text-sm">
                <button
                  onClick={() => setSelectedVerification(null)}
                  className="flex items-center text-blue-600 hover:text-blue-800 font-medium"
                >
                  <ArrowLeft className="w-4 h-4 mr-1" />
                  Back
                </button>
                <span className="text-gray-400">/</span>
                <span className="font-medium text-slate-800">
                  {selectedVerification.supplier_name} ({selectedVerification.supplier_id})
                </span>
              </div>
            ) : (
              <h2 className="text-base font-semibold text-slate-900">
                {activeTab === 'dashboard' && 'Compliance Dashboard'}
                {activeTab === 'upload' && 'Upload Documents for Verification'}
                {activeTab === 'history' && 'Supplier Verification History'}
                {activeTab === 'review' && 'Human Review Queue'}
                {activeTab === 'settings' && 'System Configuration & Database'}
              </h2>
            )}
          </div>

          <div className="flex items-center space-x-3 text-xs">
            <button
              onClick={refreshAllData}
              title="Refresh Data"
              className="flex items-center px-2.5 py-1.5 border border-gray-200 rounded text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5 text-gray-500" />
              Sync DB
            </button>
            <div className="hidden sm:flex items-center text-gray-500 border-l border-gray-200 pl-3">
              <span>PR: <strong className="text-slate-700">{prData?.pr_number || 'PR-2026-114'}</strong></span>
            </div>
          </div>
        </header>

        {/* Scrollable Body */}
        <main className="flex-1 overflow-y-auto p-6">
          {/* =========================================================================
              VIEW 1: DETAILED VERIFICATION RESULTS (When a specific audit is selected)
             ========================================================================= */}
          {selectedVerification ? (
            <div className="space-y-6 max-w-6xl mx-auto">
              {/* Overall Decision Banner */}
              <div
                className={`p-4 rounded-md border flex items-center justify-between ${
                  effectiveDecision(selectedVerification) === 'APPROVED'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : effectiveDecision(selectedVerification) === 'REJECTED'
                    ? 'bg-rose-50 border-rose-200 text-rose-900'
                    : 'bg-amber-50 border-amber-200 text-amber-900'
                }`}
              >
                <div className="flex items-center space-x-3">
                  {effectiveDecision(selectedVerification) === 'APPROVED' && (
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                  )}
                  {effectiveDecision(selectedVerification) === 'REJECTED' && (
                    <XCircle className="w-6 h-6 text-rose-600 shrink-0" />
                  )}
                  {effectiveDecision(selectedVerification) === 'NEEDS_HUMAN_REVIEW' && (
                    <AlertCircle className="w-6 h-6 text-amber-600 shrink-0" />
                  )}
                  <div>
                    <div className="text-xs uppercase tracking-wider font-bold">
                      Effective Compliance Decision
                    </div>
                    <div className="text-lg font-bold">
                      {effectiveDecision(selectedVerification).replace(/_/g, ' ')}
                    </div>
                    <div className="text-[11px] font-medium opacity-80">
                      Machine decision: {(selectedVerification.machine_decision || selectedVerification.overall_decision).replace(/_/g, ' ')}
                      {selectedVerification.human_review_decision
                        ? ` • Auditor: ${selectedVerification.human_review_decision.replace(/_/g, ' ')}`
                        : ''}
                    </div>
                    {selectedVerification.verification_notes && (
                      <div className="text-xs mt-0.5 opacity-90">
                        {selectedVerification.verification_notes}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setSelectedVerification(null)}
                    className="px-3 py-1.5 bg-white border border-gray-300 text-slate-700 text-xs font-medium rounded hover:bg-gray-50"
                  >
                    Back to List
                  </button>
                </div>
              </div>

              {/* Supplier & Verification Details */}
              <div className="bg-white border border-gray-200 rounded-md p-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div>
                  <span className="text-gray-500 block">Supplier Name</span>
                  <span className="font-semibold text-slate-900 text-sm">{selectedVerification.supplier_name}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Supplier Identifier</span>
                  <span className="font-medium text-slate-800">{selectedVerification.supplier_id}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Purchase Request</span>
                  <span className="font-medium text-slate-800">{selectedVerification.purchase_request_id}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Submission Date</span>
                  <span className="font-medium text-slate-800">
                    {selectedVerification.submission_timestamp
                      ? new Date(selectedVerification.submission_timestamp).toLocaleString()
                      : 'N/A'}
                  </span>
                </div>
              </div>

              {/* Metrics Summary Strip */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-white border border-gray-200 rounded-md p-3 text-center">
                  <div className="text-xs text-gray-500">Passed Checks</div>
                  <div className="text-xl font-bold text-emerald-600 mt-0.5">
                    {selectedVerification.passed_checks_count}
                  </div>
                </div>
                <div className="bg-white border border-gray-200 rounded-md p-3 text-center">
                  <div className="text-xs text-gray-500">Failed Checks</div>
                  <div className="text-xl font-bold text-rose-600 mt-0.5">
                    {selectedVerification.failed_checks_count}
                  </div>
                </div>
                <div className="bg-white border border-gray-200 rounded-md p-3 text-center">
                  <div className="text-xs text-gray-500">Checks Requiring Review</div>
                  <div className="text-xl font-bold text-amber-600 mt-0.5">
                    {selectedVerification.review_checks_count}
                  </div>
                </div>
              </div>

              {/* Human Auditor Review Card (if exists) */}
              {selectedVerification.human_review && (
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                  <div className="flex items-center space-x-2 text-blue-900 font-semibold text-xs mb-2">
                    <UserCheck className="w-4 h-4 text-blue-600" />
                    <span>Auditor Dispensation & Review Record</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-blue-950">
                    <div>
                      <span className="text-blue-700 block">Auditor Name:</span>
                      <strong>{selectedVerification.human_review.reviewer_name}</strong> ({selectedVerification.human_review.reviewer_role})
                    </div>
                    <div>
                      <span className="text-blue-700 block">Decision:</span>
                      <strong>{selectedVerification.human_review.review_decision.replace(/_/g, ' ')}</strong>
                    </div>
                    <div>
                      <span className="text-blue-700 block">Reviewed At:</span>
                      <span>{new Date(selectedVerification.human_review.reviewed_at).toLocaleString()}</span>
                    </div>
                  </div>
                  {selectedVerification.human_review.comments && (
                    <div className="mt-2 text-xs text-blue-900 border-t border-blue-200 pt-2">
                      <span className="font-medium text-blue-800">Comments: </span>
                      {selectedVerification.human_review.comments}
                    </div>
                  )}
                  {selectedVerification.human_review.dispensation_reason && (
                    <div className="mt-1 text-xs text-blue-900">
                      <span className="font-medium text-blue-800">Dispensation Reason: </span>
                      {selectedVerification.human_review.dispensation_reason}
                    </div>
                  )}
                </div>
              )}

              {/* Combined Document Source Card */}
              {selectedVerification.documents && selectedVerification.documents.length > 0 && (
                <div className="bg-white border border-gray-200 rounded-md p-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-semibold text-slate-900">
                            {selectedVerification.documents[0].original_filename}
                          </span>
                          <span className="text-[11px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-medium border border-blue-200">
                            Combined Supplier Document (Quotation + Terms & Conditions)
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5 space-x-3">
                          <span>
                            Size: {(selectedVerification.documents[0].file_size / 1024).toFixed(1)} KB
                          </span>
                          <span>•</span>
                          <span>
                            Pages: {selectedVerification.documents[0].page_count}
                          </span>
                          <span>•</span>
                          <span className="text-emerald-600 font-medium">
                            Extracted across all pages
                          </span>
                        </div>
                      </div>
                    </div>

                    <a
                      href={`/api/verifications/${encodeURIComponent(selectedVerification.id)}/document`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded text-xs font-medium text-slate-700 hover:bg-gray-50 shrink-0"
                    >
                      <ExternalLink className="w-3.5 h-3.5 mr-1.5 text-gray-500" />
                      View Original PDF
                    </a>
                  </div>
                </div>
              )}

              {/* Logical Group 1: Section A - Quotation Details */}
              <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">
                      Section A: Quotation Details
                    </h3>
                    <p className="text-xs text-gray-500">
                      Extracted line items, financial totals, and tax registration from the combined document
                    </p>
                  </div>
                  <span className="text-[11px] font-mono text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded">
                    Logical Section: quotation_details
                  </span>
                </div>

                <div className="p-4 space-y-4">
                  {/* Quotation Header Metadata */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                    <div>
                      <span className="text-gray-500 block">Quotation Reference</span>
                      <span className="font-semibold text-slate-800">
                        {selectedVerification.quotation_details?.quotation_no || 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Quotation Date</span>
                      <span className="font-semibold text-slate-800">
                        {selectedVerification.quotation_details?.date_str || 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Supplier TIN</span>
                      {selectedVerification.quotation_details?.tin ? (
                        <span className="font-mono font-medium text-slate-800">
                          {selectedVerification.quotation_details.tin}
                        </span>
                      ) : (
                        <span className="text-rose-600 font-semibold bg-rose-50 px-1.5 py-0.5 rounded">
                          Missing (Rule Breach)
                        </span>
                      )}
                    </div>
                    <div>
                      <span className="text-gray-500 block">Supplier BIN</span>
                      {selectedVerification.quotation_details?.bin ? (
                        <span className="font-mono font-medium text-slate-800">
                          {selectedVerification.quotation_details.bin}
                        </span>
                      ) : (
                        <span className="text-rose-600 font-semibold bg-rose-50 px-1.5 py-0.5 rounded">
                          Missing (Rule Breach)
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Financial Totals Breakdown */}
                  <div className="bg-gray-50 border border-gray-200 rounded p-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div>
                      <span className="text-gray-500 block">Subtotal (Excl. VAT)</span>
                      <span className="font-bold text-slate-900 text-sm">
                        {selectedVerification.quotation_details?.subtotal !== undefined
                          ? `BDT ${Number(selectedVerification.quotation_details.subtotal).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                          : 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">VAT (15%)</span>
                      <span className="font-bold text-slate-900 text-sm">
                        {selectedVerification.quotation_details?.vat_amount !== undefined
                          ? `BDT ${Number(selectedVerification.quotation_details.vat_amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                          : 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Grand Total</span>
                      <span className="font-bold text-blue-700 text-sm">
                        {selectedVerification.quotation_details?.grand_total !== undefined
                          ? `BDT ${Number(selectedVerification.quotation_details.grand_total).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                          : 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Quotation Validity</span>
                      <span className="font-medium text-slate-800">
                        {selectedVerification.quotation_details?.validity_days !== undefined
                          ? `${selectedVerification.quotation_details.validity_days} days`
                          : 'Standard (30 days)'}
                      </span>
                    </div>
                  </div>

                  {/* Extracted Line Items Table */}
                  {selectedVerification.quotation_details?.items && selectedVerification.quotation_details.items.length > 0 && (
                    <div className="border border-gray-200 rounded overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 uppercase font-medium">
                          <tr>
                            <th className="py-2 px-3">Item Code</th>
                            <th className="py-2 px-3">Description</th>
                            <th className="py-2 px-3 text-right">Quoted Qty</th>
                            <th className="py-2 px-3 text-right">Unit Price</th>
                            <th className="py-2 px-3 text-right">Line Total</th>
                            <th className="py-2 px-3 text-center">Source Page</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {selectedVerification.quotation_details.items.map((item, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="py-2 px-3 font-mono font-medium text-slate-800">
                                {item.item_code}
                              </td>
                              <td className="py-2 px-3 text-slate-700">
                                {item.description}
                              </td>
                              <td className="py-2 px-3 text-right text-slate-800 font-medium">
                                {item.quantity} {item.unit}
                              </td>
                              <td className="py-2 px-3 text-right text-slate-800">
                                BDT {Number(item.unit_price).toFixed(2)}
                              </td>
                              <td className="py-2 px-3 text-right font-medium text-slate-900">
                                BDT {Number(item.line_total).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                              </td>
                              <td className="py-2 px-3 text-center font-mono text-gray-500 text-[11px]">
                                Page {item.page_number || 1}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>

              {/* Logical Group 2: Section B - Terms and Conditions */}
              <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">
                      Section B: Terms and Conditions
                    </h3>
                    <p className="text-xs text-gray-500">
                      Extracted payment schedules, delivery promises, and contractual clauses
                    </p>
                  </div>
                  <span className="text-[11px] font-mono text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded">
                    Logical Section: contract_terms
                  </span>
                </div>

                <div className="p-4 space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded">
                      <span className="text-gray-500 block mb-1">Advance Payment Terms</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-base font-bold text-slate-900">
                          {selectedVerification.contract_terms?.advance_pct !== undefined
                            ? `${selectedVerification.contract_terms.advance_pct}%`
                            : '0%'}
                        </span>
                        {selectedVerification.contract_terms?.advance_pct !== undefined && (
                          <span
                            className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${
                              selectedVerification.contract_terms.advance_pct > 20
                                ? 'bg-rose-100 text-rose-800'
                                : 'bg-emerald-100 text-emerald-800'
                            }`}
                          >
                            {selectedVerification.contract_terms.advance_pct > 20
                              ? 'Exceeds 20% limit (Rule Breach)'
                              : 'Compliant (≤ 20%)'}
                          </span>
                        )}
                      </div>
                      <span className="text-gray-400 text-[11px] mt-1 block">
                        Remaining: {selectedVerification.contract_terms?.remaining_days !== undefined
                          ? `Within ${selectedVerification.contract_terms.remaining_days} days`
                          : 'As per standard terms'}
                      </span>
                    </div>

                    <div className="p-3 bg-gray-50 border border-gray-200 rounded">
                      <span className="text-gray-500 block mb-1">Promised Delivery Timeline</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-base font-bold text-slate-900">
                          {selectedVerification.contract_terms?.delivery_days !== undefined
                            ? `${selectedVerification.contract_terms.delivery_days} days`
                            : 'N/A'}
                        </span>
                        {selectedVerification.contract_terms?.delivery_days !== undefined && (
                          <span
                            className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${
                              selectedVerification.contract_terms.delivery_days > 45
                                ? 'bg-rose-100 text-rose-800'
                                : 'bg-emerald-100 text-emerald-800'
                            }`}
                          >
                            {selectedVerification.contract_terms.delivery_days > 45
                              ? 'Exceeds 45 days limit (Rule Breach)'
                              : 'Compliant (≤ 45 days)'}
                          </span>
                        )}
                      </div>
                      <span className="text-gray-400 text-[11px] mt-1 block">
                        Measured from Purchase Order issuance
                      </span>
                    </div>

                    <div className="p-3 bg-gray-50 border border-gray-200 rounded">
                      <span className="text-gray-500 block mb-1">Late-Delivery Penalty Clause</span>
                      <div className="flex items-center space-x-2">
                        {selectedVerification.contract_terms?.penalty_clause ? (
                          <span className="inline-flex items-center text-xs font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">
                            Clause Present ({selectedVerification.contract_terms.penalty_rate_pct !== undefined ? `${selectedVerification.contract_terms.penalty_rate_pct}%/day` : 'Standard'})
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs font-semibold text-rose-800 bg-rose-100 px-2 py-0.5 rounded">
                            Clause Missing (Rule Breach)
                          </span>
                        )}
                      </div>
                      <span className="text-gray-400 text-[11px] mt-1 block">
                        Mandatory contractual requirement
                      </span>
                    </div>
                  </div>

                  {/* Late-Delivery Penalty Excerpt if available */}
                  {selectedVerification.contract_terms?.penalty_clause && (
                    <div className="text-xs">
                      <span className="text-gray-500 block mb-1 font-medium">
                        Extracted Late-Delivery Penalty Clause Text:
                      </span>
                      <pre className="p-2.5 bg-gray-50 border border-gray-200 rounded text-xs font-mono text-slate-800 whitespace-pre-wrap">
                        {selectedVerification.contract_terms.penalty_clause}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              {/* Rule Validation Table */}
              <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-800">
                    Compliance Checks & Rules ({selectedVerification.validation_results?.length || 0})
                  </h3>
                  <span className="text-xs text-gray-500">
                    Click row to expand evidence details
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 uppercase font-medium">
                      <tr>
                        <th className="py-2.5 px-4 w-16">ID</th>
                        <th className="py-2.5 px-4">Rule Name</th>
                        <th className="py-2.5 px-4 w-28">Result</th>
                        <th className="py-2.5 px-4">Details</th>
                        <th className="py-2.5 px-4 w-24 text-right">Evidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {selectedVerification.validation_results && selectedVerification.validation_results.length > 0 ? (
                        selectedVerification.validation_results.map(rule => {
                          const isExpanded = !!expandedRuleRows[rule.id];
                          return (
                            <React.Fragment key={rule.id}>
                              <tr
                                onClick={() =>
                                  setExpandedRuleRows(prev => ({
                                    ...prev,
                                    [rule.id]: !prev[rule.id]
                                  }))
                                }
                                className="hover:bg-gray-50 cursor-pointer transition-colors"
                              >
                                <td className="py-2.5 px-4 font-mono font-medium text-gray-500">
                                  {rule.rule_id}
                                </td>
                                <td className="py-2.5 px-4 font-medium text-slate-800">
                                  {rule.rule_name}
                                </td>
                                <td className="py-2.5 px-4">
                                  <span
                                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                                      rule.result === 'PASS'
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : rule.result === 'FAIL'
                                        ? 'bg-rose-100 text-rose-800'
                                        : 'bg-amber-100 text-amber-800'
                                    }`}
                                  >
                                    {rule.result}
                                  </span>
                                </td>
                                <td className="py-2.5 px-4 text-gray-600">
                                  {rule.explanation || 'Evaluated against compliance specifications.'}
                                </td>
                                <td className="py-2.5 px-4 text-right text-blue-600 font-medium">
                                  <div className="flex items-center justify-end space-x-1">
                                    <span>{isExpanded ? 'Hide' : 'View'}</span>
                                    {isExpanded ? (
                                      <ChevronUp className="w-3.5 h-3.5" />
                                    ) : (
                                      <ChevronDown className="w-3.5 h-3.5" />
                                    )}
                                  </div>
                                </td>
                              </tr>

                              {/* Expanded Row showing exact evidence & page */}
                              {isExpanded && (
                                <tr className="bg-gray-50 border-t border-b border-gray-200">
                                  <td colSpan={5} className="p-4 space-y-2">
                                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs mb-2">
                                      <div>
                                        <span className="text-gray-500 block">Actual Extracted Value:</span>
                                        <span className="font-semibold text-slate-900">{rule.actual_value || 'None'}</span>
                                      </div>
                                      <div>
                                        <span className="text-gray-500 block">Expected Condition:</span>
                                        <span className="font-semibold text-slate-900">{rule.expected_value || 'Compliant'}</span>
                                      </div>
                                      <div>
                                        <span className="text-gray-500 block">Source Document & Page:</span>
                                        <span className="font-medium text-slate-800">
                                          {rule.document || 'Document'} (Page {rule.page || 1})
                                        </span>
                                      </div>
                                    </div>
                                    <div>
                                      <span className="text-gray-500 text-xs block mb-1">
                                        Exact Text Excerpt from Source Document:
                                      </span>
                                      <pre className="p-2.5 bg-white border border-gray-200 rounded text-xs font-mono text-slate-800 whitespace-pre-wrap">
                                        {rule.evidence_text || 'Exact text logged in document stream.'}
                                      </pre>
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan={5} className="py-6 text-center text-gray-500">
                            No validation rule records saved for this verification.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Purchase Request Item Comparison Table */}
              {selectedVerification.comparison_results && selectedVerification.comparison_results.length > 0 && (
                <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                    <h3 className="text-sm font-semibold text-slate-800">
                      Line Item Comparison with {selectedVerification.purchase_request_id || prData?.pr_number || 'PR-2026-114'}
                    </h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 uppercase font-medium">
                        <tr>
                          <th className="py-2.5 px-4">Item Code</th>
                          <th className="py-2.5 px-4">Description</th>
                          <th className="py-2.5 px-4 text-right">Req. Qty</th>
                          <th className="py-2.5 px-4 text-right">Quoted Qty</th>
                          <th className="py-2.5 px-4 text-right">Max Price</th>
                          <th className="py-2.5 px-4 text-right">Quoted Price</th>
                          <th className="py-2.5 px-4 text-center">Price Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {selectedVerification.comparison_results.map((item, idx) => {
                          const priceExceeded = item.quoted_unit_price > item.max_unit_price;
                          return (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="py-2.5 px-4 font-mono font-medium text-slate-800">
                                {item.item_code}
                              </td>
                              <td className="py-2.5 px-4 text-slate-700">
                                {item.item_description}
                              </td>
                              <td className="py-2.5 px-4 text-right text-gray-600">
                                {item.requested_qty} {item.unit}
                              </td>
                              <td className="py-2.5 px-4 text-right font-medium text-slate-800">
                                {item.quoted_qty} {item.unit}
                              </td>
                              <td className="py-2.5 px-4 text-right text-gray-600">
                                BDT {item.max_unit_price.toFixed(2)}
                              </td>
                              <td className="py-2.5 px-4 text-right font-medium text-slate-800">
                                BDT {item.quoted_unit_price.toFixed(2)}
                              </td>
                              <td className="py-2.5 px-4 text-center">
                                <span
                                  className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-semibold ${
                                    priceExceeded
                                      ? 'bg-rose-100 text-rose-800'
                                      : 'bg-emerald-100 text-emerald-800'
                                  }`}
                                >
                                  {priceExceeded ? 'Exceeds Ceiling' : 'Compliant'}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : null}

          {/* =========================================================================
              VIEW 2: DASHBOARD
             ========================================================================= */}
          {!selectedVerification && activeTab === 'dashboard' && (
            <div className="space-y-6 max-w-6xl mx-auto">
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white border border-gray-200 rounded-md p-4">
                  <div className="text-xs font-medium text-gray-500">Total Verifications</div>
                  <div className="text-2xl font-bold text-slate-900 mt-1">
                    {summary.total_verifications}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">Persistent in SQLite</div>
                </div>

                <div className="bg-white border border-gray-200 rounded-md p-4">
                  <div className="text-xs font-medium text-gray-500">Approved</div>
                  <div className="text-2xl font-bold text-emerald-600 mt-1">
                    {summary.approved}
                  </div>
                  <div className="text-xs text-emerald-600 mt-1">Passed all rules</div>
                </div>

                <div className="bg-white border border-gray-200 rounded-md p-4">
                  <div className="text-xs font-medium text-gray-500">Rejected</div>
                  <div className="text-2xl font-bold text-rose-600 mt-1">
                    {summary.rejected}
                  </div>
                  <div className="text-xs text-rose-600 mt-1">Rule violations</div>
                </div>

                <div className="bg-white border border-gray-200 rounded-md p-4">
                  <div className="text-xs font-medium text-gray-500">Needs Human Review</div>
                  <div className="text-2xl font-bold text-amber-600 mt-1">
                    {summary.needs_human_review}
                  </div>
                  <div className="text-xs text-amber-600 mt-1">Action required</div>
                </div>
              </div>

              {/* Recent Verification Table / Empty State */}
              <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">Recent Verifications</h3>
                    <p className="text-xs text-gray-500">Latest supplier audits logged in SQLite</p>
                  </div>
                  {summary.total_verifications > 0 && (
                    <button
                      onClick={() => setActiveTab('history')}
                      className="text-xs font-medium text-blue-600 hover:text-blue-800"
                    >
                      View All ({summary.total_verifications})
                    </button>
                  )}
                </div>

                {summary.total_verifications === 0 ? (
                  <div className="py-16 px-4 text-center">
                    <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                    <h4 className="text-sm font-semibold text-slate-800">No supplier verifications yet</h4>
                    <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1 mb-5">
                      The SQLite database is clean and empty. Upload a combined supplier document (Quotation + Terms & Conditions) to begin automated compliance audits.
                    </p>
                    <button
                      onClick={() => setActiveTab('upload')}
                      className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-md hover:bg-blue-700 transition-colors"
                    >
                      <UploadCloud className="w-4 h-4 mr-2" />
                      Upload Supplier Document
                    </button>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 uppercase font-medium">
                        <tr>
                          <th className="py-3 px-4">Supplier</th>
                          <th className="py-3 px-4">Submission Date</th>
                          <th className="py-3 px-4 text-center">Passed</th>
                          <th className="py-3 px-4 text-center">Failed</th>
                          <th className="py-3 px-4 text-center">Review</th>
                          <th className="py-3 px-4">Decision</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {summary.recent_verifications.map(row => (
                          <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                            <td className="py-3 px-4">
                              <div className="font-semibold text-slate-900">{row.supplier_name}</div>
                              <div className="text-xs font-mono text-gray-500">{row.supplier_id}</div>
                            </td>
                            <td className="py-3 px-4 text-gray-600">
                              {row.submission_timestamp
                                ? new Date(row.submission_timestamp).toLocaleDateString()
                                : 'Recent'}
                            </td>
                            <td className="py-3 px-4 text-center font-medium text-emerald-600">
                              {row.passed_checks_count}
                            </td>
                            <td className="py-3 px-4 text-center font-medium text-rose-600">
                              {row.failed_checks_count}
                            </td>
                            <td className="py-3 px-4 text-center font-medium text-amber-600">
                              {row.review_checks_count}
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                                  effectiveDecision(row) === 'APPROVED'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : effectiveDecision(row) === 'REJECTED'
                                    ? 'bg-rose-100 text-rose-800'
                                    : 'bg-amber-100 text-amber-800'
                                }`}
                              >
                                {effectiveDecision(row).replace(/_/g, ' ')}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => viewVerificationDetails(row.id)}
                                className="text-blue-600 hover:text-blue-800 font-medium"
                              >
                                View Results
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =========================================================================
              VIEW 3: DOCUMENT UPLOAD
             ========================================================================= */}
          {!selectedVerification && activeTab === 'upload' && (
            <div className="max-w-2xl mx-auto space-y-6">
              <div className="bg-white border border-gray-200 rounded-md p-6">
                <h3 className="text-base font-semibold text-slate-900 mb-1">
                  Upload Supplier Document
                </h3>
                <p className="text-xs text-gray-500 mb-6">
                  Upload a single PDF containing the supplier quotation and terms and conditions.
                </p>

                {uploadError && (
                  <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-800 flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span>{uploadError}</span>
                  </div>
                )}

                <form onSubmit={handleUploadSubmit} className="space-y-4">
                  {/* Supplier Name */}
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Supplier Name <span className="text-gray-400">(Optional - auto-extracted from document if empty)</span>
                    </label>
                    <input
                      type="text"
                      value={uploadSupplierName}
                      onChange={e => setUploadSupplierName(e.target.value)}
                      placeholder="e.g. Apex Apparel Accessories Ltd"
                      className="w-full px-3 py-2 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </div>

                  {/* Supplier Identifier */}
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Supplier ID <span className="text-gray-400">(Optional - auto-generated if empty)</span>
                    </label>
                    <input
                      type="text"
                      value={uploadSupplierId}
                      onChange={e => setUploadSupplierId(e.target.value)}
                      placeholder="e.g. SUP-2026-001"
                      className="w-full px-3 py-2 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono"
                    />
                  </div>

                  {/* Purchase Request Selection */}
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Purchase Request Specification
                    </label>
                    <select
                      value={selectedPrId}
                      onChange={e => setSelectedPrId(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                    >
                      <option value={prData?.pr_number || "PR-2026-114"}>
                        {prData?.pr_number || "PR-2026-114"} — Aamar Garments Ltd (Procurement Directorate)
                      </option>
                    </select>
                  </div>

                  {/* Single Combined Document Upload Zone (Quotation + Terms & Conditions) */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-medium text-slate-700">
                        Supplier Document (Quotation + Terms & Conditions) <span className="text-rose-500">*</span>
                      </label>
                      <span className="text-[11px] text-gray-500">1 PDF file containing both sections</span>
                    </div>

                    <input
                      type="file"
                      accept=".pdf"
                      id="supplier-doc-upload"
                      className="hidden"
                      onChange={e => {
                        if (e.target.files && e.target.files[0]) {
                          const file = e.target.files[0];
                          if (!file.name.toLowerCase().endsWith('.pdf')) {
                            setUploadError('Only PDF files are supported.');
                            return;
                          }
                          if (file.size > 50 * 1024 * 1024) {
                            setUploadError('File exceeds 50MB maximum limit.');
                            return;
                          }
                          setSupplierDocFile(file);
                          setUploadError(null);
                        }
                      }}
                    />

                    {!supplierDocFile ? (
                      <div
                        onDragOver={e => {
                          e.preventDefault();
                          setIsDragging(true);
                        }}
                        onDragEnter={e => {
                          e.preventDefault();
                          setIsDragging(true);
                        }}
                        onDragLeave={e => {
                          e.preventDefault();
                          setIsDragging(false);
                        }}
                        onDrop={e => {
                          e.preventDefault();
                          setIsDragging(false);
                          if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                            const file = e.dataTransfer.files[0];
                            if (!file.name.toLowerCase().endsWith('.pdf')) {
                              setUploadError('Only PDF files are supported.');
                              return;
                            }
                            if (file.size > 50 * 1024 * 1024) {
                              setUploadError('File exceeds 50MB maximum limit.');
                              return;
                            }
                            setSupplierDocFile(file);
                            setUploadError(null);
                          }
                        }}
                        className={`border-2 border-dashed rounded-md p-6 text-center transition-colors cursor-pointer ${
                          isDragging
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-300 bg-gray-50 hover:bg-gray-100 hover:border-gray-400'
                        }`}
                        onClick={() => {
                          const el = document.getElementById('supplier-doc-upload');
                          if (el) el.click();
                        }}
                      >
                        <UploadCloud className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                        <div className="text-xs font-semibold text-slate-800">
                          Click to select or drag and drop supplier document
                        </div>
                        <p className="text-[11px] text-gray-500 mt-1">
                          Single PDF containing Section A (Quotation) and Section B (Terms & Conditions) • Up to 50MB
                        </p>
                      </div>
                    ) : (
                      <div className="border border-gray-200 rounded-md p-4 bg-gray-50">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3 min-w-0">
                            <div className="w-9 h-9 rounded bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                              <FileText className="w-5 h-5" />
                            </div>
                            <div className="min-w-0">
                              <div className="text-xs font-semibold text-slate-900 truncate">
                                {supplierDocFile.name}
                              </div>
                              <div className="text-[11px] text-gray-500 flex items-center space-x-2 mt-0.5">
                                <span>{(supplierDocFile.size / 1024).toFixed(1)} KB</span>
                                <span>•</span>
                                <span className="inline-flex items-center text-emerald-600 font-medium">
                                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1"></span>
                                  Ready for verification
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center space-x-2 shrink-0">
                            <button
                              type="button"
                              onClick={() => {
                                const el = document.getElementById('supplier-doc-upload');
                                if (el) el.click();
                              }}
                              className="px-2.5 py-1 text-xs border border-gray-300 rounded bg-white text-slate-700 hover:bg-gray-50"
                            >
                              Replace File
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setSupplierDocFile(null);
                                setUploadError(null);
                              }}
                              title="Remove File"
                              className="p-1 text-gray-400 hover:text-rose-600 rounded"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Submit Button & Status */}
                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={uploadLoading || !supplierDocFile}
                      className="w-full py-2.5 px-4 bg-blue-600 text-white text-xs font-semibold rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {uploadLoading ? 'Processing Verification...' : 'Verify Supplier Document'}
                    </button>

                    {uploadLoading && (
                      <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800 flex items-center space-x-2">
                        <RefreshCw className="w-4 h-4 text-blue-600 animate-spin shrink-0" />
                        <span>{uploadStatusMsg}</span>
                      </div>
                    )}
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* =========================================================================
              VIEW 4: VERIFICATION HISTORY
             ========================================================================= */}
          {!selectedVerification && activeTab === 'history' && (
            <div className="space-y-4 max-w-6xl mx-auto">
              {/* Search & Filter Bar */}
              <div className="bg-white border border-gray-200 rounded-md p-3 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="relative w-full sm:w-80">
                  <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={historySearch}
                    onChange={e => setHistorySearch(e.target.value)}
                    placeholder="Search by supplier name or ID..."
                    className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
                  <Filter className="w-3.5 h-3.5 text-gray-400" />
                  <select
                    value={historyFilter}
                    onChange={e => setHistoryFilter(e.target.value)}
                    className="px-2.5 py-1.5 border border-gray-300 rounded text-xs bg-white text-slate-700 outline-none"
                  >
                    <option value="ALL">All Decisions</option>
                    <option value="APPROVED">Approved</option>
                    <option value="REJECTED">Rejected</option>
                    <option value="NEEDS_HUMAN_REVIEW">Needs Human Review</option>
                  </select>
                </div>
              </div>

              {/* History Table */}
              <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                {verificationsList.length === 0 ? (
                  <div className="py-16 px-4 text-center">
                    <History className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                    <h4 className="text-sm font-semibold text-slate-800">No verification history available</h4>
                    <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1 mb-5">
                      Upload combined supplier documents (Quotation + Terms & Conditions) to create persistent audit records in SQLite.
                    </p>
                    <button
                      onClick={() => setActiveTab('upload')}
                      className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-md hover:bg-blue-700 transition-colors"
                    >
                      <UploadCloud className="w-4 h-4 mr-2" />
                      Upload Supplier Document
                    </button>
                  </div>
                ) : filteredVerifications.length === 0 ? (
                  <div className="py-12 text-center text-xs text-gray-500">
                    No verifications match the selected search and filter criteria.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 uppercase font-medium">
                        <tr>
                          <th className="py-3 px-4">Supplier</th>
                          <th className="py-3 px-4">Submission Date</th>
                          <th className="py-3 px-4 text-center">Passed</th>
                          <th className="py-3 px-4 text-center">Failed</th>
                          <th className="py-3 px-4 text-center">Review</th>
                          <th className="py-3 px-4">Decision</th>
                          <th className="py-3 px-4 text-right">Audit</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {filteredVerifications.map(row => (
                          <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                            <td className="py-3 px-4">
                              <div className="font-semibold text-slate-900">{row.supplier_name}</div>
                              <div className="text-xs font-mono text-gray-500">{row.supplier_id}</div>
                            </td>
                            <td className="py-3 px-4 text-gray-600">
                              {row.submission_timestamp
                                ? new Date(row.submission_timestamp).toLocaleDateString()
                                : 'Recent'}
                            </td>
                            <td className="py-3 px-4 text-center font-medium text-emerald-600">
                              {row.passed_checks_count}
                            </td>
                            <td className="py-3 px-4 text-center font-medium text-rose-600">
                              {row.failed_checks_count}
                            </td>
                            <td className="py-3 px-4 text-center font-medium text-amber-600">
                              {row.review_checks_count}
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                                  effectiveDecision(row) === 'APPROVED'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : effectiveDecision(row) === 'REJECTED'
                                    ? 'bg-rose-100 text-rose-800'
                                    : 'bg-amber-100 text-amber-800'
                                }`}
                              >
                                {effectiveDecision(row).replace(/_/g, ' ')}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => viewVerificationDetails(row.id)}
                                className="text-blue-600 hover:text-blue-800 font-medium"
                              >
                                View Details
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =========================================================================
              VIEW 5: HUMAN REVIEW QUEUE
             ========================================================================= */}
          {!selectedVerification && activeTab === 'review' && (
            <div className="max-w-6xl mx-auto space-y-4">
              {pendingReviews.length === 0 ? (
                <div className="bg-white border border-gray-200 rounded-md py-16 px-4 text-center">
                  <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
                  <h4 className="text-sm font-semibold text-slate-800">
                    No cases currently require human review
                  </h4>
                  <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1">
                    All submitted supplier verifications were processed deterministically or approved/rejected without exceptions.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  {/* Left Column: List of cases requiring review */}
                  <div className="lg:col-span-5 space-y-3">
                    <h3 className="text-sm font-semibold text-slate-900">
                      Cases Requiring Review ({pendingReviews.length})
                    </h3>
                    <div className="space-y-2">
                      {pendingReviews.map(c => {
                        const isSelected = c.id === selectedReviewCaseId;
                        return (
                          <div
                            key={c.id}
                            onClick={() => {
                              setSelectedReviewCaseId(c.id);
                              setReviewSuccessMsg(null);
                            }}
                            className={`p-3.5 border rounded-md cursor-pointer transition-colors ${
                              isSelected
                                ? 'bg-blue-50 border-blue-400'
                                : 'bg-white border-gray-200 hover:bg-gray-50'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-xs text-slate-900">
                                {c.supplier_name}
                              </span>
                              <span className="text-[11px] font-mono text-gray-500">
                                {c.supplier_id}
                              </span>
                            </div>
                            <div className="text-xs text-slate-600 line-clamp-2 mb-2">
                              {c.verification_notes || 'Requires auditor dispensation evaluation.'}
                            </div>
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded font-medium">
                                {c.review_checks_count} review item(s)
                              </span>
                              <span className="text-gray-400">
                                {c.submission_timestamp ? new Date(c.submission_timestamp).toLocaleDateString() : ''}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Right Column: Case details and auditor decision form */}
                  <div className="lg:col-span-7">
                    {activeReviewCase ? (
                      <div className="bg-white border border-gray-200 rounded-md p-5 space-y-5">
                        <div className="border-b border-gray-200 pb-3">
                          <h4 className="text-sm font-semibold text-slate-900">
                            Auditor Review for {activeReviewCase.supplier_name}
                          </h4>
                          <p className="text-xs text-gray-500 font-mono">
                            Supplier ID: {activeReviewCase.supplier_id}
                          </p>
                        </div>

                        {/* Flagged issues / evidence */}
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-2">
                            Flagged Compliance Issues:
                          </label>
                          <div className="space-y-2">
                            {activeReviewCase.flagged_issues && activeReviewCase.flagged_issues.length > 0 ? (
                              activeReviewCase.flagged_issues.map((issue, idx) => (
                                <div key={idx} className="p-2.5 bg-amber-50 border border-amber-200 rounded text-xs space-y-1">
                                  <div className="flex items-center justify-between font-semibold text-amber-900">
                                    <span>{issue.rule_id} — {issue.rule_name}</span>
                                    <span className="text-[11px] uppercase bg-amber-200 text-amber-900 px-1 rounded">
                                      {issue.result}
                                    </span>
                                  </div>
                                  <div className="text-amber-800">{issue.explanation}</div>
                                  {issue.evidence_text && (
                                    <div className="font-mono text-[11px] text-slate-700 bg-white p-1.5 rounded border border-amber-200">
                                      {issue.evidence_text}
                                    </div>
                                  )}
                                </div>
                              ))
                            ) : (
                              <div className="p-2.5 bg-gray-50 border border-gray-200 rounded text-xs text-gray-600">
                                {activeReviewCase.verification_notes || 'Flagged for human procurement audit review.'}
                              </div>
                            )}
                          </div>
                        </div>

                        {reviewSuccessMsg && (
                          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-800 flex items-center space-x-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                            <span>{reviewSuccessMsg}</span>
                          </div>
                        )}

                        {/* Review Form */}
                        <form onSubmit={handleReviewSubmit} className="space-y-4 pt-2 border-t border-gray-200">
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs font-medium text-slate-700 mb-1">
                                Reviewer Name <span className="text-rose-500">*</span>
                              </label>
                              <input
                                type="text"
                                required
                                value={reviewerName}
                                onChange={e => setReviewerName(e.target.value)}
                                placeholder="e.g. Tariq Ahmed"
                                className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500"
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-slate-700 mb-1">
                                Reviewer Role
                              </label>
                              <input
                                type="text"
                                value={reviewerRole}
                                onChange={e => setReviewerRole(e.target.value)}
                                placeholder="e.g. Procurement Auditor"
                                className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500"
                              />
                            </div>
                          </div>

                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">
                              Review Decision <span className="text-rose-500">*</span>
                            </label>
                            <select
                              value={reviewDecision}
                              onChange={e => setReviewDecision(e.target.value)}
                              className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs bg-white outline-none focus:ring-1 focus:ring-blue-500"
                            >
                              <option value="APPROVED_WITH_DISPENSATION">
                                Approve with Dispensation (Within Tolerable Threshold)
                              </option>
                              <option value="REJECTED">
                                Reject Supplier (Policy Breach)
                              </option>
                              <option value="ESCALATED">
                                Escalate to Senior Procurement Committee
                              </option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">
                              Dispensation Reason / Justification
                            </label>
                            <input
                              type="text"
                              value={reviewDispensationReason}
                              onChange={e => setReviewDispensationReason(e.target.value)}
                              placeholder="e.g. Price deviation is below 3% ceiling; lead time is manageable"
                              className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">
                              Auditor Comments & Audit Trail Notes
                            </label>
                            <textarea
                              rows={2}
                              value={reviewComments}
                              onChange={e => setReviewComments(e.target.value)}
                              placeholder="Enter permanent audit comments..."
                              className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>

                          <button
                            type="submit"
                            disabled={reviewSubmitting || !reviewerName.trim()}
                            className="w-full py-2 bg-blue-600 text-white text-xs font-semibold rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
                          >
                            {reviewSubmitting ? 'Recording Decision...' : 'Submit Review Decision'}
                          </button>
                        </form>
                      </div>
                    ) : (
                      <div className="bg-white border border-gray-200 rounded-md p-8 text-center text-xs text-gray-500">
                        Select a case from the left column to view issues and record auditor review.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =========================================================================
              VIEW 6: SETTINGS & DATABASE MANAGEMENT
             ========================================================================= */}
          {!selectedVerification && activeTab === 'settings' && (
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Database Architecture Info */}
              <div className="bg-white border border-gray-200 rounded-md p-5">
                <h3 className="text-sm font-semibold text-slate-900 mb-1">
                  Database & Persistence Configuration
                </h3>
                <p className="text-xs text-gray-500 mb-4">
                  The application uses an authoritative SQLite database for all supplier verification records.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded">
                    <span className="text-gray-500 block">Database Location:</span>
                    <span className="font-mono text-slate-800">./data/supplier_verification.db</span>
                  </div>
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded">
                    <span className="text-gray-500 block">ORM Layer:</span>
                    <span className="font-semibold text-slate-800">SQLAlchemy 2.1 (Python)</span>
                  </div>
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded">
                    <span className="text-gray-500 block">Upload Storage:</span>
                    <span className="font-mono text-slate-800">./data/uploads/ (Disk-safe PDF storage)</span>
                  </div>
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded">
                    <span className="text-gray-500 block">Total Database Records:</span>
                    <span className="font-semibold text-slate-800">{summary.total_verifications} verifications</span>
                  </div>
                </div>
              </div>

              {/* Reference Purchase Request Specifications */}
              <div className="bg-white border border-gray-200 rounded-md p-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">
                      Reference Purchase Request ({prData?.pr_number || 'PR-2026-114'})
                    </h3>
                    <p className="text-xs text-gray-500">
                      Aamar Garments Ltd Procurement Baseline Items
                    </p>
                  </div>
                  <span className="text-xs font-mono bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                    {prData?.items.length || 0} line items
                  </span>
                </div>

                <div className="overflow-x-auto border border-gray-200 rounded">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 uppercase font-medium">
                      <tr>
                        <th className="py-2 px-3">Item Code</th>
                        <th className="py-2 px-3">Description</th>
                        <th className="py-2 px-3 text-right">Quantity</th>
                        <th className="py-2 px-3 text-right">Max Unit Price</th>
                        <th className="py-2 px-3 text-right">Target Days</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {prData?.items.map(item => (
                        <tr key={item.item_code} className="hover:bg-gray-50">
                          <td className="py-2 px-3 font-mono font-medium text-slate-800">
                            {item.item_code}
                          </td>
                          <td className="py-2 px-3 text-slate-700">
                            {item.item_description}
                          </td>
                          <td className="py-2 px-3 text-right text-gray-600">
                            {item.quantity} {item.unit}
                          </td>
                          <td className="py-2 px-3 text-right font-medium text-slate-800">
                            BDT {item.max_unit_price.toFixed(2)}
                          </td>
                          <td className="py-2 px-3 text-right text-gray-600">
                            {item.target_delivery_days} days
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Reset to Clean Zero State */}
              <div className="bg-white border border-rose-200 rounded-md p-5">
                <h3 className="text-sm font-semibold text-rose-900 mb-1">
                  Database Clean Reset
                </h3>
                <p className="text-xs text-rose-700 mb-4">
                  Permanently clear all verification records, validation results, and human reviews in SQLite. Leaves the baseline Purchase Request intact and resets the application to 0 records.
                </p>

                {resetConfirmOpen ? (
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={handleResetDatabase}
                      disabled={resettingDb}
                      className="px-3 py-1.5 bg-rose-600 text-white text-xs font-semibold rounded hover:bg-rose-700 transition-colors disabled:opacity-50"
                    >
                      {resettingDb ? 'Resetting...' : 'Yes, Delete All Verifications'}
                    </button>
                    <button
                      onClick={() => setResetConfirmOpen(false)}
                      className="px-3 py-1.5 bg-gray-100 text-gray-700 text-xs font-semibold rounded hover:bg-gray-200"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setResetConfirmOpen(true)}
                    className="inline-flex items-center px-3 py-1.5 bg-white border border-rose-300 text-rose-700 text-xs font-semibold rounded hover:bg-rose-50 transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5 mr-1.5 text-rose-600" />
                    Reset Verifications to Clean Zero State
                  </button>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
