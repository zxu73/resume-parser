import { Experience } from '../components/ExperienceManager';

export interface SwapItem {
  resume_experience_title: string;
  pool_title: string;
  pool_company: string;
  pool_duration: string;
  pool_description: string;
}

export interface ApplySwapsResult {
  docId: string;
  modifiedResumeText: string;
}

export function useExperienceSwap() {
  const analyzeSwaps = async (
    resumeText: string,
    jobDescription: string,
    poolExperiences: Experience[],
  ): Promise<any> => {
    const res = await fetch('/analyze-experience-swaps', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_text: resumeText,
        job_description: jobDescription,
        pool_experiences: poolExperiences.map((exp) => ({
          title: exp.title,
          company: exp.company,
          duration: exp.duration,
          description: exp.description,
          skills: exp.skills,
        })),
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error: ${res.status} ${res.statusText}`);
    }

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.message || 'Analysis failed');
    }

    return data;
  };

  const applySwaps = async (
    docId: string,
    swaps: SwapItem[],
    fallbackResumeText: string,
  ): Promise<ApplySwapsResult> => {
    const res = await fetch('/apply-swaps-docx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_id: docId, swaps }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to apply swaps to document');
    }

    const data = await res.json();
    if (!data.success) {
      throw new Error('Failed to apply swaps to document');
    }

    return {
      docId: data.doc_id,
      modifiedResumeText: data.modified_resume_text || fallbackResumeText,
    };
  };

  return { analyzeSwaps, applySwaps };
}
