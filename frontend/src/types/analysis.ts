// TypeScript interfaces matching the backend schema

export interface StructuredEvaluation {
  executive_summary: string;
  overall_score: number;
  job_match_percentage: number;
  strengths: string[];
  weaknesses: string[];
  missing_skills: string[];
  matching_skills: string[];
}

export interface DetailedRating {
  score: number;
  justification: string;
}

export interface ParaphrasingSuggestion {
  current_text: string;
  suggested_text: string;
  keywords_added?: string[];
  job_requirement_reference: string;
  alignment_reason: string;
}

export interface PriorityRecommendation {
  priority: 'High' | 'Medium' | 'Low';
  title: string;
  description: string;
  specific_example: string;
  paraphrasing_suggestion?: ParaphrasingSuggestion;
}

export interface StructuredRating {
  detailed_ratings: {
    content_quality: DetailedRating;
    skills_match: DetailedRating;
    experience_relevance: DetailedRating;
  };
  keyword_suggestions: PriorityRecommendation[];
  star_suggestions: PriorityRecommendation[];
}

export interface AnalysisResult {
  success: boolean;
  structured_evaluation?: StructuredEvaluation;
  structured_rating?: StructuredRating;
  workflow_type: string;
  message: string;
}
