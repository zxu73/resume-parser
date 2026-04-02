import React, { useState, useCallback, useRef, useEffect } from 'react';
import mammoth from 'mammoth';
import { StructuredRating, PriorityRecommendation } from '../types/analysis';
import { Button } from './ui/button';

// ── Types ──────────────────────────────────────────────────────────────────

interface ResumePreviewProps {
  docId?: string;
  resumeText?: string;   // fallback for plain-text uploads
  rating: StructuredRating;
}

type SectionKey = 'keyword' | 'star';

interface Change {
  idx: number;          // global index used for approve/skip sets
  rec: PriorityRecommendation;
  currentText: string;
  suggestedText: string;
  reason: string;
  section: SectionKey;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function buildChanges(rating: StructuredRating): Change[] {
  const changes: Change[] = [];
  let idx = 0;
  (rating.keyword_suggestions ?? []).forEach((rec) => {
    const s = rec.paraphrasing_suggestion;
    if (s?.current_text && s?.suggested_text) {
      changes.push({ idx: idx++, rec, currentText: s.current_text, suggestedText: s.suggested_text, reason: s.alignment_reason, section: 'keyword' });
    }
  });
  (rating.star_suggestions ?? []).forEach((rec) => {
    const s = rec.paraphrasing_suggestion;
    if (s?.current_text && s?.suggested_text) {
      changes.push({ idx: idx++, rec, currentText: s.current_text, suggestedText: s.suggested_text, reason: s.alignment_reason, section: 'star' });
    }
  });
  return changes;
}

// ── Highlight CSS (injected once) ─────────────────────────────────────────

const HIGHLIGHT_STYLE = `
.pdf-highlight-active {
  background: rgba(251, 191, 36, 0.45);
  outline: 2px solid #f59e0b;
  border-radius: 2px;
  cursor: default;
}
.pdf-highlight-done {
  background: rgba(34, 197, 94, 0.3);
  outline: 2px solid #22c55e;
  border-radius: 2px;
}
`;

// ── Sub-components ─────────────────────────────────────────────────────────

const SECTION_LABELS: Record<SectionKey, string> = {
  keyword: 'Missing Skills',
  star: 'STAR Improvements',
};

const ChangeCard: React.FC<{
  change: Change;
  total: number;
  activeIdx: number;
  approved: Set<number>;
  skipped: Set<number>;
  onApprove: () => void;
  onSkip: () => void;
  onNav: (dir: -1 | 1) => void;
  onDownload: () => void;
  isDownloading: boolean;
  downloadLabel: string;
}> = ({ change, total, activeIdx, approved, skipped, onApprove, onSkip, onNav, onDownload, isDownloading, downloadLabel }) => {
  const isApproved = approved.has(change.idx);
  const isSkipped = skipped.has(change.idx);
  const approvedCount = approved.size;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-200">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          {SECTION_LABELS[change.section]} · {activeIdx + 1} of {total}
        </span>
        <span className="text-xs text-gray-400">
          {approvedCount} approved · {skipped.size} skipped
        </span>
      </div>

      {/* Job title */}
      <p className="text-sm font-semibold text-gray-800 mb-4">{change.rec.title}</p>

      {/* Current sentence */}
      <div className="mb-3">
        <p className="text-xs font-medium text-red-600 uppercase tracking-wide mb-1">Current</p>
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-800 leading-relaxed">"{change.currentText}"</p>
        </div>
      </div>

      {/* Suggested sentence */}
      <div className="mb-3">
        <p className="text-xs font-medium text-green-600 uppercase tracking-wide mb-1">Suggested</p>
        <div className="p-3 bg-green-50 border border-green-200 rounded-md">
          <p className="text-sm text-green-800 font-medium leading-relaxed">"{change.suggestedText}"</p>
        </div>
      </div>

      {/* Reason */}
      <div className="mb-5">
        <p className="text-xs font-medium text-blue-600 uppercase tracking-wide mb-1">Why this improves job fit</p>
        <p className="text-xs text-gray-600 leading-relaxed">{change.reason}</p>
      </div>

      {/* Approve / Skip */}
      {isApproved ? (
        <div className="flex items-center gap-2 mb-4 p-2 bg-green-50 border border-green-200 rounded-md">
          <span className="text-green-700 text-sm font-medium">Approved</span>
        </div>
      ) : isSkipped ? (
        <div className="flex items-center gap-2 mb-4 p-2 bg-gray-50 border border-gray-200 rounded-md">
          <span className="text-gray-500 text-sm">Skipped</span>
        </div>
      ) : (
        <div className="flex gap-2 mb-4">
          <Button onClick={onApprove} className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm">
            Approve
          </Button>
          <Button onClick={onSkip} variant="outline" className="flex-1 text-sm">
            Skip
          </Button>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between mb-6">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onNav(-1)}
          disabled={activeIdx === 0}
        >
          ← Prev
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onNav(1)}
          disabled={activeIdx === total - 1}
        >
          Next →
        </Button>
      </div>

      {/* Download */}
      <div className="mt-auto pt-3 border-t border-gray-200">
        <Button
          onClick={onDownload}
          disabled={approvedCount === 0 || isDownloading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm"
        >
          {isDownloading ? 'Generating…' : downloadLabel}
        </Button>
      </div>
    </div>
  );
};

// ── Fallback text view (for TXT uploads) ─────────────────────────────────

const TextFallback: React.FC<{ resumeText: string; changes: Change[]; approved: Set<number> }> = ({
  resumeText,
  changes,
  approved,
}) => {
  const lines = resumeText.split('\n');
  const approvedMap = new Map(
    changes
      .filter((c) => approved.has(c.idx))
      .map((c) => [c.currentText.trim(), c.suggestedText])
  );
  const activeTexts = new Set(changes.map((c) => c.currentText.trim()));

  return (
    <div
      className="max-w-[700px] mx-auto bg-white shadow-md rounded p-10"
      style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
    >
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (approvedMap.has(trimmed)) {
          return (
            <p key={i} className="text-sm leading-relaxed text-green-800 bg-green-50 rounded px-1 my-0.5">
              {approvedMap.get(trimmed)}
            </p>
          );
        }
        if (activeTexts.has(trimmed)) {
          return (
            <p key={i} className="text-sm leading-relaxed text-amber-800 bg-amber-50 border-l-2 border-amber-400 px-2 my-0.5">
              {line}
            </p>
          );
        }
        return (
          <p key={i} className="text-sm leading-relaxed text-gray-800 my-0.5">
            {line || <br />}
          </p>
        );
      })}
    </div>
  );
};

// ── Main component ─────────────────────────────────────────────────────────

export const ResumePreview: React.FC<ResumePreviewProps> = ({ docId, resumeText, rating }) => {
  const changes = buildChanges(rating);
  const keywordChanges = changes.filter((c) => c.section === 'keyword');
  const starChanges = changes.filter((c) => c.section === 'star');

  const [activeSection, setActiveSection] = useState<SectionKey>('keyword');
  const [keywordIdx, setKeywordIdx] = useState(0);
  const [starIdx, setStarIdx] = useState(0);
  const [approved, setApproved] = useState<Set<number>>(new Set());
  const [skipped, setSkipped] = useState<Set<number>>(new Set());
  const [isDownloading, setIsDownloading] = useState(false);
  const [docHtml, setDocHtml] = useState<string>('');
  const [docLoading, setDocLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const sectionChanges = activeSection === 'keyword' ? keywordChanges : starChanges;
  const sectionIdx = activeSection === 'keyword' ? keywordIdx : starIdx;
  const setSectionIdx = activeSection === 'keyword' ? setKeywordIdx : setStarIdx;

  // Load Word document via mammoth when docId is provided
  useEffect(() => {
    if (!docId) return;
    setDocLoading(true);
    fetch(`/resume-doc/${docId}`)
      .then((r) => r.arrayBuffer())
      .then((buf) => mammoth.convertToHtml({ arrayBuffer: buf }))
      .then((result) => setDocHtml(result.value))
      .catch((err) => console.error('mammoth conversion failed:', err))
      .finally(() => setDocLoading(false));
  }, [docId]);

  const activeChange = sectionChanges[sectionIdx];

  const handleApprove = useCallback(() => {
    if (!activeChange) return;
    setApproved((prev) => new Set([...prev, activeChange.idx]));
    if (sectionIdx < sectionChanges.length - 1) setSectionIdx((i) => i + 1);
  }, [activeChange, sectionIdx, sectionChanges.length, setSectionIdx]);

  const handleSkip = useCallback(() => {
    if (!activeChange) return;
    setSkipped((prev) => new Set([...prev, activeChange.idx]));
    if (sectionIdx < sectionChanges.length - 1) setSectionIdx((i) => i + 1);
  }, [activeChange, sectionIdx, sectionChanges.length, setSectionIdx]);

  const handleNav = useCallback((dir: -1 | 1) => {
    setSectionIdx((i) => Math.max(0, Math.min(sectionChanges.length - 1, i + dir)));
  }, [sectionChanges.length, setSectionIdx]);


  const handleDownload = useCallback(async () => {
    if (approved.size === 0) return;
    setIsDownloading(true);

    const replacements = changes
      .filter((c) => approved.has(c.idx))
      .map((c) => ({ current_text: c.currentText, suggested_text: c.suggestedText }));

    try {
      const res = await fetch('/download-modified-docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docId, replacements }),
      });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'improved-resume.docx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download error:', err);
      alert('Failed to generate the modified document. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  }, [docId, approved, changes]);

  const activeText = activeChange?.currentText ?? '';
  const approvedTexts = new Set(
    changes.filter((c) => approved.has(c.idx)).map((c) => c.currentText)
  );

  // Highlight matching paragraphs in the rendered DOM instead of
  // doing regex on the HTML string (which breaks when mammoth splits
  // text across <strong>, <a>, <em>, etc.).
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !docHtml) return;

    const stripBullet = (s: string) =>
      s.replace(/^[\s•·\-–—*○▪►◆▸]+/, '').trim();
    const normWs = (s: string) => s.replace(/\s+/g, ' ').trim();

    // Remove old highlights
    container.querySelectorAll('.pdf-highlight-active, .pdf-highlight-done').forEach((el) => {
      el.classList.remove('pdf-highlight-active', 'pdf-highlight-done');
    });

    const findBlock = (rawText: string): Element | null => {
      if (!rawText) return null;
      const body = normWs(stripBullet(rawText)).toLowerCase();
      if (body.length < 10) return null;
      const anchor = body.slice(0, 40);

      const blocks = container.querySelectorAll('p, li');
      for (const block of blocks) {
        const blockText = normWs(block.textContent || '').toLowerCase();
        if (blockText.includes(anchor)) return block;
      }
      return null;
    };

    // Green highlights for approved changes
    for (const t of approvedTexts) {
      const el = findBlock(t);
      if (el) el.classList.add('pdf-highlight-done');
    }

    // Amber highlight for active change (applied last so it wins)
    const activeEl = findBlock(activeText);
    if (activeEl) {
      activeEl.classList.add('pdf-highlight-active');
      activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [activeSection, sectionIdx, activeText, approvedTexts, docHtml]);

  if (changes.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        No paraphrasing suggestions available for this analysis.
      </div>
    );
  }

  return (
    <>
      {/* Inject highlight CSS once */}
      <style>{HIGHLIGHT_STYLE}</style>

      <div className="flex gap-4 items-start">
        {/* ── Left: document viewer ────────────────────── */}
        <div
          ref={containerRef}
          className="flex-1 overflow-y-auto border border-gray-200 rounded-lg bg-gray-50"
          style={{ maxHeight: '88vh' }}
        >
          {docId ? (
            /* ── Word document viewer via mammoth ── */
            docLoading ? (
              <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
                Loading document…
              </div>
            ) : docHtml ? (
              <div
                className="p-8 bg-white shadow-sm"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: '13px', lineHeight: 1.5 }}
                dangerouslySetInnerHTML={{ __html: docHtml }}
              />
            ) : (
              <div className="flex items-center justify-center h-64 text-red-500 text-sm p-4">
                Could not load document. Make sure the backend is running.
              </div>
            )
          ) : resumeText ? (
            <TextFallback resumeText={resumeText} changes={changes} approved={approved} />
          ) : null}
        </div>

        {/* ── Right: tab bar + change card ─────────────── */}
        <div
          className="w-[400px] shrink-0 bg-white border border-gray-200 rounded-lg"
          style={{ minHeight: '500px', maxHeight: '88vh', overflowY: 'auto' }}
        >
          {/* Tab bar */}
          <div className="flex border-b border-gray-200">
            {(['keyword', 'star'] as SectionKey[]).map((key) => {
              const count = key === 'keyword' ? keywordChanges.length : starChanges.length;
              const label = SECTION_LABELS[key];
              const isActive = activeSection === key;
              return (
                <button
                  key={key}
                  onClick={() => setActiveSection(key)}
                  className={`flex-1 py-3 text-xs font-semibold tracking-wide transition-colors ${
                    isActive
                      ? 'border-b-2 border-blue-600 text-blue-700 bg-blue-50'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {label}
                  <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-xs ${isActive ? 'bg-blue-200 text-blue-800' : 'bg-gray-200 text-gray-600'}`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Active change card */}
          <div className="p-5">
            {activeChange ? (
              <ChangeCard
                change={activeChange}
                total={sectionChanges.length}
                activeIdx={sectionIdx}
                approved={approved}
                skipped={skipped}
                onApprove={handleApprove}
                onSkip={handleSkip}
                onNav={handleNav}
                onDownload={handleDownload}
                isDownloading={isDownloading}
                downloadLabel={`Download ${docId ? '.docx' : 'PDF'} (${approved.size} change${approved.size !== 1 ? 's' : ''} applied)`}
              />
            ) : (
              <p className="text-gray-400 text-sm text-center mt-10">No changes in this section.</p>
            )}
          </div>
        </div>
      </div>
    </>
  );
};
