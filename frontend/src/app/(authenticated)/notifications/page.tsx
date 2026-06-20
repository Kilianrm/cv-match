"use client";

import { useEffect, useState } from "react";
import { Bell, Save } from "lucide-react";
import { apiClient } from "@/lib/api-client";

const notificationsApiEnabled = process.env.NEXT_PUBLIC_NOTIFICATIONS_API === "true";

type NotificationPreferences = {
  daily_digest_enabled: boolean;
  match_alerts_enabled: boolean;
  optimization_updates_enabled: boolean;
};

const defaultPreferences: NotificationPreferences = {
  daily_digest_enabled: true,
  match_alerts_enabled: true,
  optimization_updates_enabled: true,
};

export default function NotificationsPage() {
  const [preferences, setPreferences] = useState<NotificationPreferences>(defaultPreferences);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!notificationsApiEnabled) {
      setLoading(false);
      return;
    }

    async function loadPreferences() {
      try {
        const payload = await apiClient("/api/v1/notifications/preferences");
        setPreferences({ ...defaultPreferences, ...payload });
      } catch {
        // Keep default values if backend endpoint is not ready yet.
      } finally {
        setLoading(false);
      }
    }

    void loadPreferences();
  }, []);

  async function savePreferences() {
    if (!notificationsApiEnabled) {
      setMessage("Notifications backend is not enabled yet.");
      return;
    }

    setSaving(true);
    setMessage(null);

    try {
      await apiClient("/api/v1/notifications/preferences", {
        method: "PUT",
        body: JSON.stringify(preferences),
      });

      setMessage("Notification preferences saved.");
    } catch {
      setMessage("Could not save preferences right now.");
    } finally {
      setSaving(false);
    }
  }

  function updatePreference<K extends keyof NotificationPreferences>(key: K, value: boolean) {
    setPreferences((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-8">
      <header className="rounded-xl border border-primary/15 bg-surface p-6">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary/10 p-2 text-primary">
            <Bell size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Notification Center</h1>
            <p className="text-sm text-muted">Manage what updates you receive from CV Match.</p>
          </div>
        </div>
      </header>

      <section className="space-y-4 rounded-xl border border-primary/15 bg-surface p-6">
        <PreferenceRow
          title="Daily match digest"
          description="Receive a daily email with your best new job matches."
          checked={preferences.daily_digest_enabled}
          disabled={loading || saving}
          onChange={(value) => updatePreference("daily_digest_enabled", value)}
        />

        <PreferenceRow
          title="Instant match alerts"
          description="Get notified when high-score opportunities appear."
          checked={preferences.match_alerts_enabled}
          disabled={loading || saving}
          onChange={(value) => updatePreference("match_alerts_enabled", value)}
        />

        <PreferenceRow
          title="Optimization updates"
          description="Get notified when CV optimization results are ready."
          checked={preferences.optimization_updates_enabled}
          disabled={loading || saving}
          onChange={(value) => updatePreference("optimization_updates_enabled", value)}
        />
      </section>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={savePreferences}
          disabled={loading || saving}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Save size={16} />
          {saving ? "Saving..." : "Save preferences"}
        </button>

        {message ? <p className="text-sm text-muted">{message}</p> : null}
      </div>
    </div>
  );
}

type PreferenceRowProps = {
  title: string;
  description: string;
  checked: boolean;
  disabled: boolean;
  onChange: (value: boolean) => void;
};

function PreferenceRow({ title, description, checked, disabled, onChange }: PreferenceRowProps) {
  return (
    <label className="flex items-start justify-between gap-4 rounded-lg border border-primary/10 p-4">
      <span>
        <span className="block text-sm font-semibold text-foreground">{title}</span>
        <span className="block text-sm text-muted">{description}</span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1 h-5 w-5 cursor-pointer accent-primary"
      />
    </label>
  );
}
