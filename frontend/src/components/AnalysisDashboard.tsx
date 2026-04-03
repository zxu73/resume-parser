import React from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { ResumePreview } from './ResumePreview';
import { StructuredEvaluation, StructuredRating } from '../types/analysis';

interface AnalysisDashboardProps {
  evaluation: StructuredEvaluation;
  rating: StructuredRating;
  originalResumeText?: string;
  docId?: string;
}

const ScoreBar: React.FC<{ score: number; maxScore: number; label: string }> = ({ score, maxScore, label }) => {
  const percentage = (score / maxScore) * 100;
  const getColor = (pct: number) => {
    if (pct >= 80) return 'bg-green-500';
    if (pct >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span className="font-semibold">{score}/{maxScore}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${getColor(percentage)}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

function computeBetterCVScore(evaluation: StructuredEvaluation, rating: StructuredRating): number {
  // Weighted composite (0–100):
  //   40% job keyword match (deterministic, from matching/missing skill counts)
  //   35% overall quality (LLM evaluation)
  //   25% experience relevance (LLM rating)
  const jobMatch = evaluation.job_match_percentage * 0.40;
  const quality  = (evaluation.overall_score / 10) * 100 * 0.35;
  const relevance = (rating.detailed_ratings.experience_relevance.score / 10) * 100 * 0.25;
  return Math.round(jobMatch + quality + relevance);
}

export const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({ evaluation, rating, originalResumeText, docId }) => {
  if (!evaluation || !rating) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-yellow-800">
          Structured analysis data not available. The system may still be processing or using legacy format.
        </p>
      </div>
    );
  }

  const betterCVScore = computeBetterCVScore(evaluation, rating);
  const scoreColor = betterCVScore >= 80 ? 'text-green-600' : betterCVScore >= 60 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="space-y-6">
      {/* Executive Summary & Overall Scores */}
      <Card className="p-6">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-2xl font-bold">Executive Summary</h2>
          <div className="text-right">
            <div className={`text-5xl font-bold ${scoreColor}`}>{betterCVScore}</div>
            <div className="text-xs text-gray-500 mt-1">BetterCV Score / 100</div>
          </div>
        </div>
        <p className="text-gray-700 mb-4">{evaluation.executive_summary}</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <div>
            <h3 className="font-semibold mb-3">Overall Scores</h3>
            <ScoreBar score={evaluation.overall_score} maxScore={10} label="Overall Quality" />
            <div className="mb-3">
              <div className="flex justify-between text-sm mb-1">
                <span>Keyword Match</span>
                <span className="font-semibold">{evaluation.job_match_percentage}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${evaluation.job_match_percentage >= 80 ? 'bg-green-500' :
                    evaluation.job_match_percentage >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${evaluation.job_match_percentage}%` }}
                />
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-3">Detailed Ratings</h3>
            <ScoreBar score={rating.detailed_ratings.content_quality.score} maxScore={10} label="Content Quality" />
            <ScoreBar score={rating.detailed_ratings.experience_relevance.score} maxScore={10} label="Experience Relevance" />
          </div>
        </div>
      </Card>

      {/* Skills Analysis */}
      <Card className="p-6">
        <h2 className="text-xl font-bold mb-4">Skills Analysis</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold text-green-700 mb-3">Matching Skills ({evaluation.matching_skills?.length || 0})</h3>
            <div className="flex flex-wrap gap-2">
              {evaluation.matching_skills?.map((skill, index) => (
                <Badge key={index} className="bg-green-100 text-green-800">{skill}</Badge>
              )) || <span className="text-gray-500">No matching skills found</span>}
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-red-700 mb-3">Missing Skills ({evaluation.missing_skills?.length || 0})</h3>
            <div className="flex flex-wrap gap-2">
              {evaluation.missing_skills?.map((skill, index) => (
                <Badge key={index} className="bg-red-100 text-red-800">{skill}</Badge>
              )) || <span className="text-gray-500">No missing skills identified</span>}
            </div>
          </div>
        </div>
      </Card>

      {/* Strengths & Weaknesses */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4 text-green-700">Strengths</h2>
          <ul className="space-y-2">
            {evaluation.strengths?.map((strength, index) => (
              <li key={index} className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                <span className="text-gray-700">{strength}</span>
              </li>
            )) || <li className="text-gray-500">No strengths identified</li>}
          </ul>
        </Card>

        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4 text-red-700">Areas for Improvement</h2>
          <ul className="space-y-2">
            {evaluation.weaknesses?.map((weakness, index) => (
              <li key={index} className="flex items-start">
                <span className="text-red-500 mr-2">⚠</span>
                <span className="text-gray-700">{weakness}</span>
              </li>
            )) || <li className="text-gray-500">No weaknesses identified</li>}
          </ul>
        </Card>
      </div>

      {/* Resume Preview & Changes */}
      {(docId || originalResumeText) && (
        <ResumePreview
          docId={docId}
          resumeText={originalResumeText}
          rating={rating}
        />
      )}
    </div>
  );
};
