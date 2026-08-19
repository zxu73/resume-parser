import React, { useState, useRef } from 'react';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';
import { AnalysisDashboard } from './components/AnalysisDashboard';
import { ExperienceManager, Experience } from './components/ExperienceManager';
import { SwapReview } from './components/SwapReview';
import { ClarifyingQuestions } from './components/ClarifyingQuestions';
import {
  AnalysisResult,
  ClarifyingQuestion,
  QuestionAnswer,
  StructuredEvaluation,
} from './types/analysis';
import { useResumeUpload } from './hooks/useResumeUpload';
import { useResumeEvaluation } from './hooks/useResumeEvaluation';
import { useExperienceSwap, SwapItem } from './hooks/useExperienceSwap';

export default function App() {
  // State management
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [swapRecommendations, setSwapRecommendations] = useState<any>(null);
  const [resumeText, setResumeText] = useState<string>('');
  const [docId, setDocId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [pendingEvaluation, setPendingEvaluation] = useState<StructuredEvaluation | null>(null);
  const [pendingQuestions, setPendingQuestions] = useState<ClarifyingQuestion[] | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const { uploadResume } = useResumeUpload();
  const { evaluateResume, finalizeAnalysis } = useResumeEvaluation();
  const { analyzeSwaps, applySwaps } = useExperienceSwap();

  // File upload handler
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type — Word (.docx) only
      const allowedTypes = [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      ];

      if (!allowedTypes.includes(file.type)) {
        setError('Please upload a Word document (.docx)');
        return;
      }

      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        setError('File size must be less than 10MB');
        return;
      }

      setSelectedFile(file);
      setError(null);
    }
  };

  // Start analysis
  const startAnalysis = async () => {
    if (!selectedFile || !jobDescription.trim()) {
      setError('Please upload a resume and provide a job description');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const { resumeText: text, docId: id } = await uploadResume(selectedFile);
      setResumeText(text);
      if (id) setDocId(id);

      if (experiences.length > 0) {
        const swapData = await analyzeSwaps(text, jobDescription, experiences);
        setSwapRecommendations(swapData.optimization_analysis);
      } else {
        const evalRes = await evaluateResume(text, jobDescription);
        setPendingEvaluation(evalRes.structured_evaluation);
        setPendingQuestions(evalRes.clarifying_questions || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Called by ClarifyingQuestions component with the collected answers (or [] on skip).
  const handleAnswerSubmit = async (answers: QuestionAnswer[]) => {
    if (!pendingEvaluation || !resumeText) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      const result = await finalizeAnalysis(
        resumeText,
        jobDescription,
        pendingEvaluation,
        answers,
      );
      setAnalysisResult(result);
      setPendingQuestions(null);
      setPendingEvaluation(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Finalization failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle accepting swaps
  const handleAcceptSwaps = async () => {
    if (!swapRecommendations || !resumeText || !docId) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const swaps: SwapItem[] = swapRecommendations.comparisons
        .filter((c: any) => c.should_replace)
        .map((comparison: any) => {
          const poolExp = experiences[comparison.pool_experience_index];
          return {
            resume_experience_title: comparison.resume_experience_title,
            pool_title: poolExp.title,
            pool_company: poolExp.company || '',
            pool_duration: poolExp.duration || '',
            pool_description: poolExp.description || '',
          };
        });

      const { docId: newDocId, modifiedResumeText } = await applySwaps(docId, swaps, resumeText);
      setDocId(newDocId);
      setResumeText(modifiedResumeText);

      const evalRes = await evaluateResume(modifiedResumeText, jobDescription);
      setPendingEvaluation(evalRes.structured_evaluation);
      setPendingQuestions(evalRes.clarifying_questions || []);
      setSwapRecommendations(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply swaps and analyze');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle rejecting swaps (continue with original resume)
  const handleRejectSwaps = async () => {
    if (!resumeText) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const evalRes = await evaluateResume(resumeText, jobDescription);
      setPendingEvaluation(evalRes.structured_evaluation);
      setPendingQuestions(evalRes.clarifying_questions || []);
      setSwapRecommendations(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Reset form
  const resetForm = () => {
    setSelectedFile(null);
    setJobDescription('');
    setExperiences([]);
    setSwapRecommendations(null);
    setResumeText('');
    setDocId(null);
    setAnalysisResult(null);
    setPendingEvaluation(null);
    setPendingQuestions(null);
    setIsAnalyzing(false);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>BetterCV</h1>
      <p>Upload your resume and job description to get AI-powered feedback</p>

      {/* Error Display */}
      {error && (
        <div style={{
          backgroundColor: '#ffebee',
          border: '1px solid #f44336',
          padding: '10px',
          marginBottom: '20px',
          borderRadius: '4px',
          color: '#d32f2f'
        }}>
          Error: {error}
        </div>
      )}

      {/* File Upload */}
      <div style={{ marginBottom: '20px' }}>
        <h2>1. Upload Resume</h2>
        <p style={{ color: '#d32f2f', fontSize: '13px', marginBottom: '8px' }}>
          Only Word documents (.docx) are accepted.
        </p>
        <label
          style={{
            display: 'inline-block',
            padding: '10px 24px',
            backgroundColor: '#1976d2',
            color: '#fff',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '14px',
          }}
        >
          Choose .docx File
          <input
            ref={fileInputRef}
            type="file"
            accept=".docx"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </label>
        {selectedFile && (
          <div style={{ color: 'green', marginTop: '8px' }}>
            ✓ Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
          </div>
        )}
      </div>

      {/* Job Description */}
      <div style={{ marginBottom: '20px' }}>
        <h2>2. Job Description</h2>
        <Textarea
          placeholder="Paste the job description here..."
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          style={{ width: '100%', minHeight: '150px', marginBottom: '10px' }}
        />
        <div style={{ fontSize: '14px', color: '#666' }}>
          {jobDescription.length} characters
        </div>
      </div>

      {/* Experience Pool Manager */}
      <div style={{ marginBottom: '20px' }}>
        <h2>3. Additional Experiences (Optional)</h2>
        <div style={{
          backgroundColor: '#e3f2fd',
          padding: '15px',
          borderRadius: '8px',
          marginBottom: '15px',
          fontSize: '14px'
        }}>
          <strong>💡 Smart Feature:</strong> Add all your work experiences here.
          Our AI will automatically select the best ones that match the job and
          ensure your resume fits on 1 page by removing less relevant experiences.
        </div>
        <ExperienceManager
          experiences={experiences}
          onExperiencesChange={setExperiences}
        />
      </div>

      {/* Action Buttons */}
      <div style={{ marginBottom: '30px' }}>
        <Button
          onClick={startAnalysis}
          disabled={!selectedFile || !jobDescription.trim() || isAnalyzing}
          style={{ marginRight: '10px' }}
        >
          {isAnalyzing ? 'Analyzing...' : 'Start Analysis'}
        </Button>

        {(selectedFile || jobDescription || analysisResult || experiences.length > 0) && (
          <Button onClick={resetForm} variant="outline">
            Reset
          </Button>
        )}
      </div>

      {/* Loading State */}
      {isAnalyzing && (
        <div style={{
          backgroundColor: '#e3f2fd',
          padding: '20px',
          borderRadius: '4px',
          marginBottom: '20px'
        }}>
          <h3>Analysis in Progress...</h3>
          {experiences.length > 0 ? (
            <div>
              <p><strong>Smart Optimization Mode Active</strong></p>
              <p>AI is comparing your {experiences.length} pool experience(s) with resume experiences...</p>
              <p style={{ fontSize: '14px', marginTop: '10px' }}>
                Step 1: Analyzing relevance scores…<br/>
                Step 2: Deciding optimal swaps…<br/>
                Step 3: Rephrasing for job alignment…
              </p>
            </div>
          ) : (
            <p>AI agents are analyzing your resume. This may take a minute.</p>
          )}
        </div>
      )}

      {/* Swap Review (Step 1 results) */}
      {swapRecommendations && !isAnalyzing && (
        <div>
          <h2>4. Review Experience Swaps</h2>
          <SwapReview
            comparisons={swapRecommendations.comparisons || []}
            poolExperiences={experiences}
            onAcceptAll={handleAcceptSwaps}
            onReject={handleRejectSwaps}
          />
        </div>
      )}

      {/* Clarifying Questions (between evaluation and rating) */}
      {pendingQuestions && !swapRecommendations && !analysisResult && (
        <div>
          <h2>4. Clarify Your Experience</h2>
          <ClarifyingQuestions
            questions={pendingQuestions}
            onSubmit={handleAnswerSubmit}
            onSkip={() => handleAnswerSubmit([])}
            isSubmitting={isAnalyzing}
          />
        </div>
      )}

      {/* Results */}
      {analysisResult && !swapRecommendations && !pendingQuestions && (
        <div>
          <h2>4. Analysis Results</h2>

          <div className="mt-6">
            {analysisResult.structured_evaluation && analysisResult.structured_rating ? (
              <AnalysisDashboard
                evaluation={analysisResult.structured_evaluation}
                rating={analysisResult.structured_rating}
                originalResumeText={resumeText}
                docId={docId ?? undefined}
                jobDescription={jobDescription}
              />
            ) : (
              <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h3 className="font-semibold text-yellow-800 mb-2">Analysis Data Unavailable</h3>
                <p className="text-yellow-700">
                  {analysisResult.message || 'Unable to retrieve complete analysis. Please try again.'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
