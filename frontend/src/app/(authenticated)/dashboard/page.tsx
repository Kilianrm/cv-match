"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle, AlertCircle, Clock, TrendingUp } from "lucide-react";

interface ProfileData {
  user_id: string;
  email: string;
  full_name?: string;
  headline?: string;
  profile_completion_percent?: number;
  location?: string;
}

interface CVStatus {
  cv_id: string;
  original_filename: string;
  uploaded_at: string;
  parse_status: "pending" | "processing" | "completed" | "failed";
}

export default function Dashboard() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [cvStatus, setCvStatus] = useState<CVStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY_BASE_URL || "http://localhost:8080";
        const profileRes = await fetch(`${baseUrl}/api/v1/profile`, {
          credentials: "include",
        });

        if (profileRes.ok) {
          const data = await profileRes.json();
          setProfile(data);
        } else if (profileRes.status === 401) {
          setError("Session expired. Please log in again.");
        } else {
          setError("Failed to load profile");
        }

        // TODO: fetch CV status from API when endpoint is ready
        // const cvRes = await fetch(`${baseUrl}/api/v1/cv/current`, {
        //   credentials: "include",
        // });
        // if (cvRes.ok) {
        //   setCvStatus(await cvRes.json());
        // }
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "processing":
        return <Clock className="w-5 h-5 text-yellow-500" />;
      case "failed":
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse">Loading your dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-foreground">
          Welcome, {profile?.full_name || "Job Seeker"}!
        </h1>
        <p className="text-muted mt-2">
          {profile?.headline || "Find your perfect job match"}
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Profile Completion Card */}
        <div className="bg-surface border border-primary/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-foreground">Profile Status</h3>
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              <User className="w-6 h-6 text-primary" />
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-3xl font-bold text-primary">
              {profile?.profile_completion_percent || 0}%
            </p>
            <p className="text-sm text-muted">Profile Completion</p>
            <Link
              href="/profile"
              className="inline-block mt-4 text-primary hover:text-primary/80 font-medium text-sm"
            >
              Complete Profile ?
            </Link>
          </div>
        </div>

        {/* CV Status Card */}
        <div className="bg-surface border border-primary/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-foreground">CV Status</h3>
            <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center">
              {cvStatus ? getStatusIcon(cvStatus.parse_status) : <AlertCircle className="w-6 h-6 text-accent" />}
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm text-muted">
              {cvStatus ? `${cvStatus.parse_status}` : "No CV uploaded"}
            </p>
            {cvStatus && (
              <p className="text-xs text-muted">
                {new Date(cvStatus.uploaded_at).toLocaleDateString()}
              </p>
            )}
            <Link
              href="/cv-upload"
              className="inline-block mt-4 text-accent hover:text-accent/80 font-medium text-sm"
            >
              {cvStatus ? "Update CV" : "Upload CV"} ?
            </Link>
          </div>
        </div>

        {/* Job Matches Card */}
        <div className="bg-surface border border-primary/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-foreground">Job Matches</h3>
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-3xl font-bold text-foreground">0</p>
            <p className="text-sm text-muted">Available Matches</p>
            <Link
              href="/matches"
              className="inline-block mt-4 text-foreground hover:text-foreground/80 font-medium text-sm"
            >
              View Matches ?
            </Link>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-surface border border-primary/10 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            href="/cv-upload"
            className="p-4 border border-primary/10 rounded-lg hover:bg-primary/5 transition-colors"
          >
            <p className="font-semibold text-foreground">Upload or Update CV</p>
            <p className="text-sm text-muted mt-1">
              Add your CV to find job matches instantly
            </p>
          </Link>
          <Link
            href="/profile"
            className="p-4 border border-primary/10 rounded-lg hover:bg-primary/5 transition-colors"
          >
            <p className="font-semibold text-foreground">Edit Profile</p>
            <p className="text-sm text-muted mt-1">
              Update your professional information
            </p>
          </Link>
        </div>
      </div>
    </div>
  );
}

import { User } from "lucide-react";
