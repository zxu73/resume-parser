export interface UploadResult {
  resumeText: string;
  docId: string | null;
}

export function useResumeUpload() {
  const uploadResume = async (file: File): Promise<UploadResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch('/upload-resume', { method: 'POST', body: formData });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to upload resume');
    }

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || 'Resume upload failed');
    }

    return {
      resumeText: data.extracted_text || data.analysis || `Resume for ${file.name}`,
      docId: data.doc_id ?? null,
    };
  };

  return { uploadResume };
}
