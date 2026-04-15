import { AnalysisResult } from '../types/analysis';

export function useResumeEvaluation() {
  const evaluateResume = async (
    resumeText: string,
    jobDescription: string,
  ): Promise<AnalysisResult> => {
    const res = await fetch('/evaluate-resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: resumeText, job_description: jobDescription }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error: ${res.status} ${res.statusText}`);
    }

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.message || 'Analysis failed');
    }

    return data as AnalysisResult;
  };

  return { evaluateResume };
}
