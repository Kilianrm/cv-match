"use client";

import { useEffect, useState } from "react";
import { User, MapPin, Briefcase } from "lucide-react";

interface Skill {
  skill_name: string;
  category?: string;
  proficiency_level?: string;
}

interface Experience {
  position: string;
  company: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
}

interface Education {
  degree: string;
  institution: string;
  end_date?: string;
}

interface ProfileData {
  user_id: string;
  email: string;
  full_name?: string;
  headline?: string;
  summary?: string;
  location?: string;
  years_experience?: number;
  remote_preference?: string;
  skills?: Skill[];
  experience?: Experience[];
  education?: Education[];
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProfile() {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY_BASE_URL || "http://localhost:8080";
        const res = await fetch(`${baseUrl}/api/v1/profile`, {
          credentials: "include",
        });

        if (res.ok) {
          const data = await res.json();
          setProfile(data);
        } else if (res.status === 401) {
          setError("Session expired");
        } else {
          setError("Failed to load profile");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    }

    fetchProfile();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse">Loading profile...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-700">
        No profile data found
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-primary/80 rounded-lg p-8 text-background">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-4xl font-bold">{profile.full_name || "Your Profile"}</h1>
            <p className="text-lg mt-2 opacity-90">{profile.headline || "Professional"}</p>
            <div className="flex items-center gap-6 mt-4">
              <div className="flex items-center gap-2">
                <MapPin size={18} />
                <span>{profile.location || "Location not set"}</span>
              </div>
              <div className="flex items-center gap-2">
                <Briefcase size={18} />
                <span>{profile.years_experience || 0} years experience</span>
              </div>
            </div>
          </div>
          <div className="w-20 h-20 bg-background rounded-full flex items-center justify-center">
            <User size={40} className="text-primary" />
          </div>
        </div>
      </div>

      {/* About Section */}
      {profile.summary && (
        <div className="bg-surface border border-primary/10 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">About</h2>
          <p className="text-muted leading-relaxed">{profile.summary}</p>
        </div>
      )}

      {/* Skills Section */}
      {profile.skills && profile.skills.length > 0 && (
        <div className="bg-surface border border-primary/10 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Skills</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {profile.skills.map((skill, idx) => (
              <div
                key={idx}
                className="bg-primary/5 border border-primary/20 rounded-lg p-3"
              >
                <p className="font-medium text-foreground">{skill.skill_name}</p>
                {skill.proficiency_level && (
                  <p className="text-sm text-muted">{skill.proficiency_level}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Experience Section */}
      {profile.experience && profile.experience.length > 0 && (
        <div className="bg-surface border border-primary/10 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Experience</h2>
          <div className="space-y-4">
            {profile.experience.map((exp, idx) => (
              <div key={idx} className="border-l-4 border-primary pl-4">
                <p className="font-semibold text-foreground">{exp.position}</p>
                <p className="text-primary font-medium">{exp.company}</p>
                <p className="text-sm text-muted mt-1">
                  {exp.start_date ? new Date(exp.start_date).getFullYear() : "Start"} -
                  {exp.is_current ? " Present" : ` ${exp.end_date ? new Date(exp.end_date).getFullYear() : "End"}`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Education Section */}
      {profile.education && profile.education.length > 0 && (
        <div className="bg-surface border border-primary/10 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Education</h2>
          <div className="space-y-4">
            {profile.education.map((edu, idx) => (
              <div key={idx} className="border-l-4 border-accent pl-4">
                <p className="font-semibold text-foreground">{edu.degree}</p>
                <p className="text-accent font-medium">{edu.institution}</p>
                {edu.end_date && (
                  <p className="text-sm text-muted mt-1">
                    {new Date(edu.end_date).getFullYear()}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Button */}
      <div className="flex gap-4">
        <button className="px-6 py-3 bg-primary text-background rounded-lg font-semibold hover:bg-primary/90 transition-colors">
          Edit Profile
        </button>
        <button className="px-6 py-3 border border-primary/20 text-foreground rounded-lg font-semibold hover:bg-primary/5 transition-colors">
          View as Public
        </button>
      </div>
    </div>
  );
}
