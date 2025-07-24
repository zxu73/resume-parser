import React, { useState, useRef } from 'react';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';

// Types
interface AnalysisResult {
  success: boolean;
  evaluation_report: string;
  rating_and_generation: string;
  workflow_type: string;
  message: string;
}

export default function App() {
  // State management
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
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
        
        const uploadResponse = await fetch('http://localhost:8000/upload-resume', {
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

      // Call the main evaluation endpoint
      const evaluationResponse = await fetch('http://localhost:8000/evaluate-resume', {
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
        const errorData = await evaluationResponse.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const result = await evaluationResponse.json();
      
      if (!result.success) {
        throw new Error(result.message || 'Analysis failed');
      }
      
      setAnalysisResult(result);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Reset form
  const resetForm = () => {
    setSelectedFile(null);
    setJobDescription('');
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
          <p>AI agents are analyzing your resume. This may take a minute.</p>
        </div>
      )}

      {/* Results */}
      {analysisResult && (
        <div>
          <h2>3. Analysis Results</h2>
          
          {/* Evaluation Report */}
          <div style={{ marginBottom: '30px' }}>
            <h3>Evaluation Report</h3>
            <div style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '15px', 
              borderRadius: '4px',
              maxHeight: '400px',
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              fontFamily: 'monospace',
              fontSize: '14px'
            }}>
              {analysisResult.evaluation_report}
            </div>
          </div>

          {/* Ratings & Improved Resume */}
          <div style={{ marginBottom: '30px' }}>
            <h3>Ratings & Improved Resume</h3>
            <div style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '15px', 
              borderRadius: '4px',
              maxHeight: '400px',
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              fontFamily: 'monospace',
              fontSize: '14px'
            }}>
              {analysisResult.rating_and_generation}
            </div>
          </div>

          {/* Download Options */}
          <div>
            <h3>Download Options</h3>
            <Button 
              style={{ marginRight: '10px' }}
              onClick={() => {
                const content = `EVALUATION REPORT:\n${analysisResult.evaluation_report}\n\nRATINGS & IMPROVED RESUME:\n${analysisResult.rating_and_generation}`;
                const blob = new Blob([content], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'resume-analysis-report.txt';
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              Download Analysis Report (TXT)
            </Button>
            <Button 
              variant="outline"
              onClick={() => {
                navigator.clipboard.writeText(analysisResult.rating_and_generation);
                alert('Improved resume copied to clipboard!');
              }}
            >
              Copy Improved Resume
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
