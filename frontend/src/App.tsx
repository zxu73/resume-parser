import React, { useState, useRef } from 'react';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';
import { AnalysisDashboard } from './components/AnalysisDashboard';
import { ExperienceManager, Experience } from './components/ExperienceManager';
import { SwapReview } from './components/SwapReview';
import { AnalysisResult } from './types/analysis';

export default function App() {
  // State management
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [swapRecommendations, setSwapRecommendations] = useState<any>(null);
  const [resumeText, setResumeText] = useState<string>('');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File upload handler
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTypes = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
      ];
      
      if (!allowedTypes.includes(file.type)) {
        setError('Please upload a PDF, DOC, DOCX, or TXT file');
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

  // Extract text from resume file
  const extractResumeText = async (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (file.type === 'text/plain') {
          resolve(event.target?.result as string);
        } else {
          resolve('FILE_UPLOAD_REQUIRED');
        }
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
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
      let resumeText = '';
      
      // Extract resume text or upload file to backend
      if (selectedFile.type === 'text/plain') {
        resumeText = await extractResumeText(selectedFile);
      } else {
        // Upload PDF, DOC, DOCX files to backend for processing
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        const uploadResponse = await fetch('/upload-resume', {
          method: 'POST',
          body: formData
        });
        
        if (!uploadResponse.ok) {
          const errorData = await uploadResponse.json();
          throw new Error(errorData.detail || 'Failed to upload resume');
        }
        
        const uploadResult = await uploadResponse.json();
        
        if (!uploadResult.success) {
          throw new Error(uploadResult.error || 'Resume analysis failed');
        }
        
        resumeText = uploadResult.analysis || `Resume analysis for ${selectedFile.name}`;
      }

      // Store resume text for later use
      setResumeText(resumeText);

      // If pool experiences provided, use two-step workflow
      if (experiences.length > 0) {
        // Step 1: Get swap recommendations
        const analyzeResponse = await fetch('/analyze-experience-swaps', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            resume_text: resumeText,
            job_description: jobDescription,
            pool_experiences: experiences.map(exp => ({
              title: exp.title,
              company: exp.company,
              duration: exp.duration,
              description: exp.description,
              skills: exp.skills
            }))
          })
        });

        if (!analyzeResponse.ok) {
          let errorMessage = 'Analysis failed';
          try {
            const errorData = await analyzeResponse.json();
            errorMessage = errorData.detail || errorMessage;
          } catch (e) {
            errorMessage = `Server error: ${analyzeResponse.status} ${analyzeResponse.statusText}`;
          }
          throw new Error(errorMessage);
        }

        let analyzeResult;
        try {
          analyzeResult = await analyzeResponse.json();
        } catch (e) {
          throw new Error('Invalid response from server. Please check if backend is running.');
        }
        
        if (!analyzeResult.success) {
          throw new Error(analyzeResult.message || 'Analysis failed');
        }

        // Show swap recommendations for user review
        setSwapRecommendations(analyzeResult.optimization_analysis);
      } else {
        // No pool experiences - use regular evaluation
        const evaluationResponse = await fetch('/evaluate-resume', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            resume_text: resumeText,
            job_description: jobDescription
          })
        });

      if (!evaluationResponse.ok) {
        let errorMessage = 'Analysis failed';
        try {
          const errorData = await evaluationResponse.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          // If JSON parsing fails, use status text
          errorMessage = `Server error: ${evaluationResponse.status} ${evaluationResponse.statusText}`;
        }
        throw new Error(errorMessage);
      }

        let result;
        try {
          result = await evaluationResponse.json();
        } catch (e) {
          throw new Error('Invalid response from server. Please check if backend is running properly.');
        }
        
        if (!result.success) {
          throw new Error(result.message || 'Analysis failed');
        }
        
        setAnalysisResult(result);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle accepting swaps
  const handleAcceptSwaps = async () => {
    if (!swapRecommendations || !resumeText) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      // Apply swaps locally in the frontend
      let modifiedResume = resumeText;
      let swapsApplied = 0;

      swapRecommendations.comparisons
        .filter((c: any) => c.should_replace)
        .forEach((comparison: any) => {
          const poolExp = experiences[comparison.pool_experience_index];
          const oldTitle = comparison.resume_experience_title;
          
          // Try to find and replace the experience by title
          if (modifiedResume.includes(oldTitle)) {
            // Find the experience block (from title to next double newline or title)
            const titleIndex = modifiedResume.indexOf(oldTitle);
            const afterTitle = modifiedResume.substring(titleIndex);
            const endMatch = afterTitle.match(/\n\n|\n[A-Z][A-Z\s]+\n/);
            const endIndex = endMatch ? titleIndex + endMatch.index! : modifiedResume.length;
            
            const newBlock = `${poolExp.title}\n${poolExp.company}\n${poolExp.duration}\n${poolExp.description}`;
            
            modifiedResume = modifiedResume.substring(0, titleIndex) + newBlock + modifiedResume.substring(endIndex);
            swapsApplied++;
          }
        });

      console.log(`Applied ${swapsApplied} swaps locally`);
      
      // Now call /evaluate-resume with modified resume
      const response = await fetch('/evaluate-resume', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          resume_text: modifiedResume,
          job_description: jobDescription
        })
      });

      if (!response.ok) {
        let errorMessage = 'Analysis failed';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          errorMessage = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      let result;
      try {
        result = await response.json();
      } catch (e) {
        throw new Error('Invalid response from server. Please check if backend is running.');
      }

      if (!result.success) {
        throw new Error(result.message || 'Analysis failed');
      }

      setAnalysisResult(result);
      setSwapRecommendations(null); // Clear recommendations

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
      const response = await fetch('/evaluate-resume', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: jobDescription
        })
      });

      if (!response.ok) {
        let errorMessage = 'Analysis failed';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          errorMessage = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      let result;
      try {
        result = await response.json();
      } catch (e) {
        throw new Error('Invalid response from server. Please check if backend is running.');
      }

      if (!result.success) {
        throw new Error(result.message || 'Analysis failed');
      }

      setAnalysisResult(result);
      setSwapRecommendations(null); // Clear recommendations

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
    setAnalysisResult(null);
    setIsAnalyzing(false);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>AI Resume Optimizer</h1>
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
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.doc,.docx,.txt"
          onChange={handleFileSelect}
          style={{ marginBottom: '10px' }}
        />
        {selectedFile && (
          <div style={{ color: 'green' }}>
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
        
        {(selectedFile || jobDescription || analysisResult) && (
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
              <p><strong>🧠 Smart Optimization Mode Active</strong></p>
              <p>AI is comparing your {experiences.length} pool experience(s) with resume experiences...</p>
              <p style={{ fontSize: '14px', marginTop: '10px' }}>
                ✓ Step 1: Analyzing relevance scores...<br/>
                ✓ Step 2: Deciding optimal swaps...<br/>
                ✓ Step 3: Rephrasing for job alignment...
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

      {/* Results */}
      {analysisResult && !swapRecommendations && (
        <div>
          <h2>4. Analysis Results</h2>
          
          <div className="mt-6">
            {analysisResult.structured_evaluation && analysisResult.structured_rating ? (
              <AnalysisDashboard 
                evaluation={analysisResult.structured_evaluation}
                rating={analysisResult.structured_rating}
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
