// TypeScript interfaces matching the backend schema

export interface SectionAnalysis {
  score: number;
  feedback: string;
}

export interface ATSCompatibility {
  score: number;
  issues: string[];
  recommendations: string[];
}

export interface StructuredEvaluation {
  executive_summary: string;
  overall_score: number;
  job_match_percentage: number;
  section_analysis: {
    contact_info: SectionAnalysis;
    professional_summary: SectionAnalysis;
    work_experience: SectionAnalysis;
    education: SectionAnalysis;
    skills: SectionAnalysis;
  };
  strengths: string[];
  weaknesses: string[];
  missing_skills: string[];
  matching_skills: string[];
  ats_compatibility: ATSCompatibility;
}

export interface DetailedRating {
  score: number;
  justification: string;
  specific_issues?: string[];
  missing_keywords?: string[];
  formatting_issues?: string[];
  match_percentage?: number;
  matching_skills?: string[];
  missing_skills?: string[];
  gaps?: string[];
  paraphrasing_opportunities?: string[];  // For experience improvements
}

export interface PriorityRecommendation {
  priority: 'High' | 'Medium' | 'Low';
  title: string;
  description: string;
  specific_example: string;
}

export interface ImprovedResume {
  contact_info: string;
  professional_summary: string;
  work_experience: string[];
  education: string;
  skills: string[];
  additional_sections: string[];
}

export interface StructuredRating {
  detailed_ratings: {
    content_quality: DetailedRating;
    ats_compatibility: DetailedRating;
    skills_match: DetailedRating;
    experience_relevance: DetailedRating;
  };
  priority_recommendations: PriorityRecommendation[];
  improved_resume: ImprovedResume;
}

export interface AnalysisResult {
  success: boolean;
  structured_evaluation?: StructuredEvaluation;
  structured_rating?: StructuredRating;
  workflow_type: string;
  message: string;
}