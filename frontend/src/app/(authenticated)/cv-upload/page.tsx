"use client";

import { useState, useRef } from "react";
import { Upload, File, Check, AlertCircle } from "lucide-react";

type UploadStatus = "idle" | "uploading" | "success" | "error";

export default function CVUploadPage() {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File) => {
    if (!file.type.includes("pdf") && !file.name.endsWith(".docx")) {
      setError("Please upload a PDF or DOCX file");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("File size must be less than 5 MB");
      return;
    }

    setFileName(file.name);
    setError(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add("border-primary", "bg-primary/5");
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove("border-primary", "bg-primary/5");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.remove("border-primary", "bg-primary/5");

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleUpload = async () => {
    if (!fileInputRef.current?.files?.[0]) {
      setError("Please select a file");
      return;
    }

    const file = fileInputRef.current.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      setStatus("uploading");
      setError(null);

      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY_BASE_URL || "http://localhost:8080";
      const res = await fetch(`${baseUrl}/api/v1/cv/upload`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (res.ok || res.status === 202) {
        const data = await res.json();
        setJobId(data.job_id);
        setStatus("success");
        setFileName(null);
      } else if (res.status === 401) {
        setError("Session expired");
        setStatus("error");
      } else if (res.status === 413) {
        setError("File is too large (max 5 MB)");
        setStatus("error");
      } else {
        const errorData = await res.json().catch(() => ({}));
        setError(errorData.message || "Upload failed");
        setStatus("error");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setStatus("error");
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-4xl font-bold text-foreground">Upload Your CV</h1>
        <p className="text-muted mt-2">
          Upload your CV in PDF or DOCX format. Our system will parse it and match you with
          relevant job opportunities.
        </p>
      </div>

      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className="border-2 border-dashed border-primary/20 rounded-lg p-12 text-center transition-colors cursor-pointer hover:border-primary/40"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          onChange={handleInputChange}
          className="hidden"
          disabled={status === "uploading"}
        />

        <div
          onClick={() => fileInputRef.current?.click()}
          className="space-y-4"
        >
          <div className="flex justify-center">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
              <Upload className="w-8 h-8 text-primary" />
            </div>
          </div>

          {status === "idle" && !fileName && (
            <>
              <div>
                <p className="text-lg font-semibold text-foreground">
                  Drag and drop your CV here
                </p>
                <p className="text-sm text-muted mt-1">or click to browse</p>
              </div>
              <p className="text-xs text-muted">PDF or DOCX, up to 5 MB</p>
            </>
          )}

          {fileName && status === "idle" && (
            <>
              <div className="flex items-center justify-center gap-2 text-foreground">
                <File className="w-5 h-5" />
                <span className="font-medium">{fileName}</span>
              </div>
              <p className="text-sm text-muted">Ready to upload</p>
            </>
          )}

          {status === "uploading" && (
            <>
              <div className="flex justify-center">
                <div className="w-6 h-6 border-3 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
              <p className="text-foreground font-medium">Uploading...</p>
            </>
          )}

          {status === "success" && (
            <>
              <div className="flex justify-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                  <Check className="w-8 h-8 text-green-600" />
                </div>
              </div>
              <p className="text-lg font-semibold text-green-600">CV Uploaded Successfully!</p>
              <p className="text-sm text-muted">
                Your CV is being processed. We'll notify you when parsing is complete.
              </p>
              {jobId && (
                <p className="text-xs text-muted">Job ID: {jobId}</p>
              )}
            </>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Upload Button (when file selected but not uploaded) */}
      {fileName && status === "idle" && (
        <div className="flex gap-4">
          <button
            onClick={handleUpload}
            className="px-6 py-3 bg-primary text-background rounded-lg font-semibold hover:bg-primary/90 transition-colors"
          >
            Upload CV
          </button>
          <button
            onClick={() => {
              setFileName(null);
              if (fileInputRef.current) {
                fileInputRef.current.value = "";
              }
            }}
            className="px-6 py-3 border border-primary/20 text-foreground rounded-lg font-semibold hover:bg-primary/5 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Info Card */}
      <div className="bg-surface border border-primary/10 rounded-lg p-6">
        <h3 className="font-semibold text-foreground mb-3">What happens next?</h3>
        <ul className="space-y-2 text-muted">
          <li className="flex gap-3">
            <span className="text-primary font-bold">1.</span>
            <span>Your CV will be parsed and analyzed for skills, experience, and education</span>
          </li>
          <li className="flex gap-3">
            <span className="text-primary font-bold">2.</span>
            <span>Your profile will be automatically updated with the extracted information</span>
          </li>
          <li className="flex gap-3">
            <span className="text-primary font-bold">3.</span>
            <span>Job matching will start immediately to find relevant opportunities</span>
          </li>
          <li className="flex gap-3">
            <span className="text-primary font-bold">4.</span>
            <span>You'll receive a daily email digest with the best matches for you</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
