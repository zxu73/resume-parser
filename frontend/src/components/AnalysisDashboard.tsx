import React, { useEffect } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { StructuredEvaluation, StructuredRating } from '../types/analysis';

interface AnalysisDashboardProps {
  evaluation: StructuredEvaluation;
  rating: StructuredRating;
  originalResumeText?: string;
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

const PriorityIcon: React.FC<{ priority: string }> = ({ priority }) => {
  const colors = {
    High: 'bg-red-100 text-red-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Low: 'bg-blue-100 text-blue-800'
  };
  
  return (
    <Badge className={colors[priority as keyof typeof colors] || colors.Low}>
      {priority}
    </Badge>
  );
};

export const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({ evaluation, rating, originalResumeText }) => {
  // Debug: Log when originalResumeText prop changes
  useEffect(() => {
    console.log('AnalysisDashboard - originalResumeText prop updated');
    console.log('  Length:', originalResumeText?.length || 0);
    console.log('  First 200 chars:', originalResumeText?.substring(0, 200) || 'N/A');
  }, [originalResumeText]);

  // Handle fallback for structured data
  if (!evaluation || !rating) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-yellow-800">
          Structured analysis data not available. The system may still be processing or using legacy format.
        </p>
      </div>
    );
  }

  // Helper function to find text by keywords
  const findTextByKeywords = (resumeText: string, searchText: string): { found: boolean; startIndex: number; endIndex: number; extractedText: string } => {
    // First try exact match
    const exactIndex = resumeText.indexOf(searchText);
    if (exactIndex !== -1) {
      return {
        found: true,
        startIndex: exactIndex,
        endIndex: exactIndex + searchText.length,
        extractedText: searchText
      };
    }

    // If exact match fails, try keyword-based matching
    // Extract meaningful keywords from the search text
    const keywords = searchText.toLowerCase()
      .split(/\s+/)
      .filter(w => w.length > 3 && !['the', 'and', 'for', 'with', 'using', 'from', 'that', 'this', 'into'].includes(w))
      .slice(0, 5); // Use first 5 meaningful words
    
    if (keywords.length < 2) {
      return { found: false, startIndex: -1, endIndex: -1, extractedText: '' };
    }
    
    // Split resume into lines/bullets
    const lines = resumeText.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const lineLower = line.toLowerCase();
      
      // Check if this line contains most of the keywords
      const matchCount = keywords.filter(keyword => lineLower.includes(keyword)).length;
      const matchRatio = matchCount / keywords.length;
      
      if (matchRatio >= 0.6 && line.length > 20) {
        // Found a likely match! Calculate its position in the full text
        const precedingText = lines.slice(0, i).join('\n');
        const startIndex = precedingText.length + (i > 0 ? 1 : 0); // +1 for newline
        const endIndex = startIndex + line.length;
        
        return {
          found: true,
          startIndex,
          endIndex,
          extractedText: line
        };
      }
    }
    
    return { found: false, startIndex: -1, endIndex: -1, extractedText: '' };
  };

  const downloadImprovedResume = () => {
    if (!originalResumeText) {
      alert('Original resume text not available. Cannot generate improved resume.');
      return;
    }

    // Debug: Check what we're working with
    console.log('Download - Original resume text length:', originalResumeText.length);
    console.log('Download - First 200 chars of original:', originalResumeText.substring(0, 200));
    console.log('Download - Number of recommendations:', rating.priority_recommendations?.length || 0);

    // Check if originalResumeText looks like an analysis report (common indicators)
    if (originalResumeText.includes('Executive Summary') || 
        originalResumeText.includes('Overall Score') ||
        originalResumeText.includes('ANALYSIS') ||
        (originalResumeText.includes('Resume') && originalResumeText.includes('analysis'))) {
      console.error('WARNING: originalResumeText appears to be an analysis report, not the resume!');
      alert('Error: The resume text appears to be an analysis report instead of the actual resume. Please re-upload your resume file.');
      return;
    }

    // Start with the original resume text
    let improvedText = originalResumeText;

    // Apply all paraphrasing suggestions from recommendations
    if (rating.priority_recommendations) {
      // First, collect all replacements with their positions
      const replacements: Array<{
        index: number;
        current_text: string;
        suggested_text: string;
        startIndex: number;
        endIndex: number;
        extractedText: string;
      }> = [];

      rating.priority_recommendations.forEach((rec, index) => {
        if (rec.paraphrasing_suggestion) {
          const { current_text, suggested_text } = rec.paraphrasing_suggestion;
          console.log(`\nDownload - Finding Recommendation ${index + 1}:`);
          console.log('  AI text:', current_text.substring(0, 100) + (current_text.length > 100 ? '...' : ''));
          
          // Try keyword-based matching (which tries exact first, then keywords)
          const result = findTextByKeywords(improvedText, current_text);
          
          if (result.found && result.extractedText) {
            const matchType = result.extractedText === current_text ? 'exact' : 'keyword';
            console.log(`  ✓ Found ${matchType} match at position:`, result.startIndex, 'to', result.endIndex);
            console.log('  Actual text:', result.extractedText.substring(0, 80) + '...');
            replacements.push({
              index,
              current_text: result.extractedText, // Use ACTUAL text from resume
              suggested_text,
              startIndex: result.startIndex,
              endIndex: result.endIndex,
              extractedText: result.extractedText
            });
          } else {
            console.log('  ✗ Text not found in resume - skipping');
          }
        }
      });

      // Sort replacements by position (DESCENDING - from end to start)
      // This way, earlier positions don't shift when we apply later replacements
      replacements.sort((a, b) => b.startIndex - a.startIndex);
      
      console.log(`\n=== Applying ${replacements.length} replacements in reverse order ===`);
      
      // Apply replacements from end to start
      let replacementsApplied = 0;
      replacements.forEach((replacement) => {
        console.log(`\nApplying Recommendation ${replacement.index + 1}:`);
        console.log('  Position:', replacement.startIndex, 'to', replacement.endIndex);
        console.log('  Replacing:', replacement.extractedText.substring(0, 80) + '...');
        console.log('  With:', replacement.suggested_text.substring(0, 80) + '...');
        
        const before = improvedText.substring(0, replacement.startIndex);
        const after = improvedText.substring(replacement.endIndex);
        improvedText = before + replacement.suggested_text + after;
        
        replacementsApplied++;
        console.log('  ✓ Applied. New length:', improvedText.length);
      });
      
      const replacementsFailed = rating.priority_recommendations.filter(r => r.paraphrasing_suggestion).length - replacementsApplied;
      console.log(`\nDownload - Summary: ${replacementsApplied} applied, ${replacementsFailed} failed`);
      
      // Debug: Show a sample of changes
      if (replacementsApplied > 0) {
        console.log('\nDownload - Verifying changes were actually made:');
        console.log('Original text length:', originalResumeText.length);
        console.log('Improved text length:', improvedText.length);
        console.log('Text actually changed:', originalResumeText !== improvedText);
        
        // Show first difference
        for (let i = 0; i < Math.min(originalResumeText.length, improvedText.length); i++) {
          if (originalResumeText[i] !== improvedText[i]) {
            console.log(`First difference at position ${i}:`);
            console.log('  Original:', originalResumeText.substring(Math.max(0, i - 50), i + 100));
            console.log('  Improved:', improvedText.substring(Math.max(0, i - 50), i + 100));
            break;
          }
        }
      }
    }

    console.log('\nDownload - Final improved text length:', improvedText.length);
    console.log('Download - First 300 chars of improved text:', improvedText.substring(0, 300));

    // Create and download the file
    const blob = new Blob([improvedText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'improved-resume.txt';
    a.click();
    URL.revokeObjectURL(url);
    
    console.log('Download - File download triggered');
  };

  return (
    <div className="space-y-6">
      {/* Executive Summary & Overall Scores */}
      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Executive Summary</h2>
        <p className="text-gray-700 mb-4">{evaluation.executive_summary}</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <div>
            <h3 className="font-semibold mb-3">Overall Scores</h3>
            <ScoreBar score={evaluation.overall_score} maxScore={10} label="Overall Quality" />
            <div className="mb-3">
              <div className="flex justify-between text-sm mb-1">
                <span>Job Match</span>
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
            <ScoreBar score={evaluation.ats_compatibility.score} maxScore={10} label="ATS Compatibility" />
          </div>
          
          <div>
            <h3 className="font-semibold mb-3">Detailed Ratings</h3>
            <ScoreBar score={rating.detailed_ratings.content_quality.score} maxScore={10} label="Content Quality" />
            <ScoreBar score={rating.detailed_ratings.skills_match.score} maxScore={10} label="Skills Match" />
            <ScoreBar score={rating.detailed_ratings.experience_relevance.score} maxScore={10} label="Experience Relevance" />
          </div>
        </div>
      </Card>

      {/* Section Analysis */}
      <Card className="p-6">
        <h2 className="text-xl font-bold mb-4">Section Analysis</h2>
        <div className="space-y-4">
          {Object.entries(evaluation.section_analysis).map(([section, analysis]) => (
            <div key={section} className="border-l-4 border-blue-500 pl-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold capitalize">{section.replace('_', ' ')}</h3>
                <Badge variant={analysis.score >= 8 ? 'default' : analysis.score >= 6 ? 'secondary' : 'destructive'}>
                  {analysis.score}/10
                </Badge>
              </div>
              <p className="text-gray-600 text-sm">{analysis.feedback}</p>
            </div>
          ))}
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

      {/* Priority Recommendations */}
      <Card className="p-6">
        <h2 className="text-xl font-bold mb-4">Priority Recommendations - Job Alignment Focus</h2>
        <div className="space-y-6">
          {rating.priority_recommendations?.map((rec, index) => (
            <div key={index} className="border rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">{rec.title}</h3>
                <PriorityIcon priority={rec.priority} />
              </div>
              <p className="text-gray-700 mb-3">{rec.description}</p>
              
              {rec.paraphrasing_suggestion && (
                <div className="bg-white border rounded-lg p-4 mb-3">
                  <h4 className="font-semibold text-blue-700 mb-3 flex items-center">
                    <span className="mr-2">✏️</span>
                    Paraphrasing Suggestion for Better Job Alignment
                  </h4>
                  
                  {/* Job Requirement Reference */}
                  <div className="mb-3 p-2 bg-blue-50 rounded border-l-4 border-blue-400">
                    <strong className="text-blue-800">Targets Job Requirement:</strong>
                    <p className="text-blue-700 text-sm mt-1">{rec.paraphrasing_suggestion.job_requirement_reference}</p>
                  </div>
                  
                  {/* Before/After Comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                    <div className="p-3 bg-red-50 border border-red-200 rounded">
                      <h5 className="font-medium text-red-800 mb-2 flex items-center">
                        <span className="mr-1">❌</span>
                        Current Text
                      </h5>
                      <p className="text-sm text-red-700 italic">"{rec.paraphrasing_suggestion.current_text}"</p>
                    </div>
                    
                    <div className="p-3 bg-green-50 border border-green-200 rounded">
                      <h5 className="font-medium text-green-800 mb-2 flex items-center">
                        <span className="mr-1">✅</span>
                        Suggested Text
                      </h5>
                      <p className="text-sm text-green-700 font-medium">"{rec.paraphrasing_suggestion.suggested_text}"</p>
                    </div>
                  </div>
                  
                  {/* Alignment Reason */}
                  <div className="p-2 bg-yellow-50 border-l-4 border-yellow-400">
                    <strong className="text-yellow-800">Why This Improves Job Fit:</strong>
                    <p className="text-yellow-700 text-sm mt-1">{rec.paraphrasing_suggestion.alignment_reason}</p>
                  </div>
                </div>
              )}
              
              {rec.specific_example && (
                <div className="bg-white border-l-4 border-blue-500 pl-3 py-2 text-sm">
                  <strong>General Guidance:</strong> {rec.specific_example}
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* ATS Issues */}
      {evaluation.ats_compatibility?.issues?.length > 0 && (
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">ATS Compatibility Issues</h2>
          <div className="space-y-3">
            {evaluation.ats_compatibility.issues.map((issue, index) => (
              <div key={index} className="flex items-start">
                <span className="text-yellow-500 mr-2">⚠</span>
                <span className="text-gray-700">{issue}</span>
              </div>
            ))}
          </div>
          
          {evaluation.ats_compatibility.recommendations?.length > 0 && (
            <div className="mt-4">
              <h3 className="font-semibold mb-2">Recommendations:</h3>
              <ul className="space-y-1">
                {evaluation.ats_compatibility.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-blue-500 mr-2">•</span>
                    <span className="text-gray-700">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Download Actions */}
      <Card className="p-6">
        <h2 className="text-xl font-bold mb-4">Download Improved Resume</h2>
        <div className="flex flex-wrap gap-3">
          <Button onClick={downloadImprovedResume}>
            Download Improved Resume (TXT)
          </Button>
          <Button 
            variant="outline"
            onClick={() => {
              if (!originalResumeText) {
                alert('Original resume text not available.');
                return;
              }

              // Apply all paraphrasing suggestions
              let improvedText = originalResumeText;
              if (rating.priority_recommendations) {
                rating.priority_recommendations.forEach((rec) => {
                  if (rec.paraphrasing_suggestion) {
                    const { current_text, suggested_text } = rec.paraphrasing_suggestion;
                    if (improvedText.includes(current_text)) {
                      improvedText = improvedText.replace(current_text, suggested_text);
                    }
                  }
                });
              }

              navigator.clipboard.writeText(improvedText);
              alert('Improved resume copied to clipboard!');
            }}
          >
            Copy to Clipboard
          </Button>
        </div>
      </Card>
    </div>
  );
};