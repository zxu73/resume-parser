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

export interface ClarifyingQuestion {
  id: string;
  question: string;
  skill_targeted: string;
  /** Verbatim resume bullet this question is about; "" when unanchored. */
  target_bullet: string;
  /** Role/company heading the bullet sits under. */
  target_experience: string;
  question_type: 'multiple_choice' | 'free_text';
  choices: string[];
}

export interface QuestionAnswer {
  question: string;
  answer: string;
  /** Echoed back so the rewriter knows which skill was confirmed... */
  skill_targeted: string;
  /** ...and which bullet to rewrite with it. */
  target_bullet: string;
}

export interface EvaluationResponse {
  success: boolean;
  structured_evaluation: StructuredEvaluation;
  clarifying_questions: ClarifyingQuestion[];
  workflow_type: string;
  message: string;
}

export interface AnalysisResult {
  success: boolean;
  structured_evaluation?: StructuredEvaluation;
  structured_rating?: StructuredRating;
  workflow_type: string;
  message: string;
}

export interface ChatSuggestion {
  current_text: string;
  suggested_text: string;
  reason: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
