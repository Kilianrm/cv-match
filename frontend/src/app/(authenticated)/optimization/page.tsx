"use client";

import { useEffect, useState } from "react";
import { Zap, Check, AlertCircle } from "lucide-react";

interface Suggestion {
  id: string;
  category: string;
  title: string;
  description: string;
  impact: "high" | "medium" | "low";
}

interface OptimizationRequest {
  id: string;
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  suggestions?: Suggestion[];
}

export default function OptimizationPage() {
  const [optimizations, setOptimizations] = useState<OptimizationRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchOptimizations() {
      try {
        // TODO: Replace with actual API endpoint when backend is ready
        // const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY_BASE_URL || "http://localhost:8080";
        // const res = await fetch(`${baseUrl}/api/v1/optimizations`, {
        //   credentials: "include",
        // });

        // For now, show placeholder
        setOptimizations([]);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
        setLoading(false);
      }
    }

    fetchOptimizations();
  }, []);

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case "high":
        return "bg-red-50 border-red-200 text-red-700";
      case "medium":
        return "bg-yellow-50 border-yellow-200 text-yellow-700";
      case "low":
        return "bg-blue-50 border-blue-200 text-blue-700";
      default:
        return "bg-gray-50 border-gray-200 text-gray-700";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse">Loading optimizations...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-foreground">CV Optimization</h1>
        <p className="text-muted mt-2">
          Get AI-powered suggestions to optimize your CV for specific job opportunities
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Error</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {optimizations.length === 0 && (
        <div className="bg-surface border border-primary/10 rounded-lg p-12 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center">
              <Zap className="w-8 h-8 text-accent" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">No Optimizations Yet</h3>
          <p className="text-muted mb-6">
            Find a job match and click "Optimize CV" to get AI-powered suggestions tailored to
            that specific opportunity.
          </p>
          <a
            href="/matches"
            className="inline-block px-6 py-3 bg-primary text-background rounded-lg font-semibold hover:bg-primary/90 transition-colors"
          >
            View Job Matches
          </a>
        </div>
      )}

      {optimizations.length > 0 && (
        <div className="space-y-6">
          {optimizations.map((opt) => (
            <div key={opt.id} className="bg-surface border border-primary/10 rounded-lg p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-foreground">
                    Optimization Request #{opt.id}
                  </h3>
                  <p className="text-sm text-muted">Job ID: {opt.job_id}</p>
                </div>
                <div
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    opt.status === "completed"
                      ? "bg-green-100 text-green-700"
                      : opt.status === "failed"
                        ? "bg-red-100 text-red-700"
                        : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {opt.status}
                </div>
              </div>

              {opt.suggestions && opt.suggestions.length > 0 && (
                <div className="space-y-3">
                  {opt.suggestions.map((suggestion) => (
                    <div
                      key={suggestion.id}
                      className={`border rounded-lg p-4 ${getImpactColor(suggestion.impact)}`}
                    >
                      <div className="flex items-start gap-3">
                        <Check className="w-5 h-5 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <p className="font-semibold">{suggestion.title}</p>
                          <p className="text-sm mt-1">{suggestion.description}</p>
                          <p className="text-xs opacity-75 mt-2">
                            Impact: <span className="font-semibold">{suggestion.impact}</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {opt.status === "completed" && (!opt.suggestions || opt.suggestions.length === 0) && (
                <p className="text-muted">No specific suggestions for this optimization.</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Info Card */}
      <div className="bg-surface border border-primary/10 rounded-lg p-6">
        <h3 className="font-semibold text-foreground mb-3">How CV Optimization Works</h3>
        <ul className="space-y-2 text-muted">
          <li className="flex gap-3">
            <span className="text-accent font-bold">?</span>
            <span>Select a job match from the Matches page</span>
          </li>
          <li className="flex gap-3">
            <span className="text-accent font-bold">?</span>
            <span>Click "Optimize CV" to analyze your CV against that job</span>
          </li>
          <li className="flex gap-3">
            <span className="text-accent font-bold">?</span>
            <span>Receive AI-powered suggestions to improve your match score</span>
          </li>
          <li className="flex gap-3">
            <span className="text-accent font-bold">?</span>
            <span>Download the optimized CV ready to submit</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
