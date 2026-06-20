"use client";

import { useEffect, useState, useRef } from "react";
import { Upload, File, Check, AlertCircle, Trash2, RefreshCw } from "lucide-react";
import { apiClient, uploadFile } from "@/lib/api-client";

type CatalogOption = {
  id?: string;
  code?: string;
  name: string;
  role_name?: string;
  skill_name?: string;
  degree_name?: string;
};

type CurrentCV = {
  id: string;
  original_filename: string;
  content_type: string;
  parse_status: string;
  uploaded_at: string;
};

type ProfilePayload = {
  user: { user_id: string; email: string };
  profile: {
    full_name?: string;
    headline?: string;
    summary?: string;
    country_code?: string | null;
    region_id?: string | null;
    city_id?: string | null;
    years_experience?: number | null;
    work_mode_preference?: string | null;
    legacy_location?: string | null;
  };
  skills: Array<{ skill_id: string; label: string; proficiency_level?: string | null }>;
  preferred_roles: Array<{ id: string; role_name: string }>;
  experience: Array<{
    id: string;
    position: string;
    company: string;
    start_date?: string | null;
    end_date?: string | null;
    is_current: boolean;
    responsibilities: string[];
  }>;
  education: Array<{
    id: string;
    degree: string;
    institution: string;
    start_date?: string | null;
    end_date?: string | null;
    status?: string | null;
  }>;
  certifications: Array<{
    id: string;
    name: string;
    issuer: string;
    issued_at?: string | null;
    expires_at?: string | null;
  }>;
};

const emptyExperience = {
  position: "",
  company: "",
  start_date: "",
  end_date: "",
  is_current: false,
  responsibilities: "",
};

const emptyEducation = {
  degree: "",
  institution: "",
  start_date: "",
  end_date: "",
  status: "",
};

const emptyCertification = {
  name: "",
  issuer: "",
  issued_at: "",
  expires_at: "",
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfilePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [countries, setCountries] = useState<CatalogOption[]>([]);
  const [regions, setRegions] = useState<CatalogOption[]>([]);
  const [cities, setCities] = useState<CatalogOption[]>([]);
  const [skillsCatalog, setSkillsCatalog] = useState<CatalogOption[]>([]);
  const [rolesCatalog, setRolesCatalog] = useState<CatalogOption[]>([]);
  const [degreeTypesCatalog, setDegreeTypesCatalog] = useState<CatalogOption[]>([]);

  const [baseForm, setBaseForm] = useState({
    full_name: "",
    headline: "",
    summary: "",
    location: "",
    country_code: "",
    region_id: "",
    city_id: "",
    years_experience: "",
    work_mode_preference: "",
  });

  const [newSkill, setNewSkill] = useState({ skill_name: "", proficiency_level: "" });
  const [newRole, setNewRole] = useState({ role_name: "" });
  const [newExperience, setNewExperience] = useState(emptyExperience);
  const [newEducation, setNewEducation] = useState(emptyEducation);
  const [newCertification, setNewCertification] = useState(emptyCertification);

  const [roleError, setRoleError] = useState<string | null>(null);
  const [skillError, setSkillError] = useState<string | null>(null);

  const [currentCV, setCurrentCV] = useState<CurrentCV | null>(null);
  const [cvUploadStatus, setCvUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [cvDeleteStatus, setCvDeleteStatus] = useState<"idle" | "deleting" | "error">("idle");
  const [cvError, setCvError] = useState<string | null>(null);
  const [cvFileName, setCvFileName] = useState<string | null>(null);
  const cvFileInputRef = useRef<HTMLInputElement>(null);

  async function loadProfile() {
    try {
      setError(null);
      const data = (await apiClient("/api/v1/profile")) as ProfilePayload;
      setProfile(data);
      setBaseForm({
        full_name: data.profile.full_name || "",
        headline: data.profile.headline || "",
        summary: data.profile.summary || "",
        location: data.profile.legacy_location || "",
        country_code: data.profile.country_code || "",
        region_id: data.profile.region_id || "",
        city_id: data.profile.city_id || "",
        years_experience:
          data.profile.years_experience !== null && data.profile.years_experience !== undefined
            ? String(data.profile.years_experience)
            : "",
        work_mode_preference: data.profile.work_mode_preference || "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }

  async function loadCatalogs() {
    try {
      const [countriesData, skillsData, rolesData, degreeTypesData] = await Promise.all([
        apiClient("/api/v1/locations/countries"),
        apiClient("/api/v1/catalogs/skills?limit=300"),
        apiClient("/api/v1/catalogs/roles?limit=200"),
        apiClient("/api/v1/catalogs/degree-types?limit=200"),
      ]);
      setCountries(countriesData.countries || []);
      setSkillsCatalog(skillsData.skills || []);
      setRolesCatalog(rolesData.roles || []);
      setDegreeTypesCatalog(degreeTypesData.degree_types || []);
    } catch {
      // Catalogs are optional for rendering the page.
    }
  }

  async function fetchCV() {
    try {
      const data = await apiClient("/api/v1/profile/cv");
      if (data?.cv) {
        setCurrentCV(data.cv);
      }
    } catch (err) {
      console.error("Failed to fetch CV:", err);
    }
  }

  async function loadRegions(countryCode: string) {
    if (!countryCode) {
      setRegions([]);
      return;
    }
    const data = await apiClient(`/api/v1/locations/regions?country_code=${countryCode}`);
    setRegions(data.regions || []);
  }

  async function loadCities(countryCode: string, regionId: string) {
    if (!countryCode || !regionId) {
      setCities([]);
      return;
    }
    const data = await apiClient(`/api/v1/locations/cities?country_code=${countryCode}&region_id=${regionId}`);
    setCities(data.cities || []);
  }

  useEffect(() => {
    loadProfile();
    loadCatalogs();
    fetchCV();
  }, []);

  useEffect(() => {
    if (baseForm.country_code) {
      void loadRegions(baseForm.country_code);
    } else {
      setRegions([]);
    }
  }, [baseForm.country_code]);

  useEffect(() => {
    if (baseForm.country_code && baseForm.region_id) {
      void loadCities(baseForm.country_code, baseForm.region_id);
    } else {
      setCities([]);
    }
  }, [baseForm.country_code, baseForm.region_id]);

  async function saveBaseProfile() {
    try {
      setMessage(null);
      await apiClient("/api/v1/profile", {
        method: "PUT",
        body: JSON.stringify({
          full_name: baseForm.full_name,
          headline: baseForm.headline || null,
          summary: baseForm.summary || null,
          location: baseForm.location || null,
          country_code: baseForm.country_code || null,
          region_id: baseForm.region_id || null,
          city_id: baseForm.city_id || null,
          years_experience: baseForm.years_experience ? Number(baseForm.years_experience) : null,
          work_mode_preference: baseForm.work_mode_preference || null,
        }),
      });
      setMessage("Base profile updated");
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update profile");
    }
  }

  async function addSkill() {
    try {
      setSkillError(null);
      await apiClient("/api/v1/profile/skills", {
        method: "POST",
        body: JSON.stringify({
          skill_name: newSkill.skill_name,
          proficiency_level: newSkill.proficiency_level || null,
        }),
      });
      setNewSkill({ skill_name: "", proficiency_level: "" });
      await loadProfile();
    } catch (err) {
      setSkillError(err instanceof Error ? err.message : "Failed to add skill");
    }
  }

  async function removeSkill(skillId: string) {
    try {
      await apiClient(`/api/v1/profile/skills/${skillId}`, { method: "DELETE" });
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove skill");
    }
  }

  async function addRole() {
    try {
      setRoleError(null);
      await apiClient("/api/v1/profile/preferred-roles", {
        method: "POST",
        body: JSON.stringify({ role_name: newRole.role_name }),
      });
      setNewRole({ role_name: "" });
      await loadProfile();
    } catch (err) {
      setRoleError(err instanceof Error ? err.message : "Failed to add role");
    }
  }

  async function deleteRole(roleId: string) {
    try {
      await apiClient(`/api/v1/profile/preferred-roles/${roleId}`, { method: "DELETE" });
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove role");
    }
  }

  async function addExperience() {
    try {
      await apiClient("/api/v1/profile/experience", {
        method: "POST",
        body: JSON.stringify({
          position: newExperience.position,
          company: newExperience.company,
          start_date: newExperience.start_date,
          end_date: newExperience.end_date || null,
          is_current: newExperience.is_current,
          responsibilities: newExperience.responsibilities
            .split("\n")
            .map((x) => x.trim())
            .filter(Boolean),
        }),
      });
      setNewExperience(emptyExperience);
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add experience");
    }
  }

  async function deleteExperience(id: string) {
    try {
      await apiClient(`/api/v1/profile/experience/${id}`, { method: "DELETE" });
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove experience");
    }
  }

  async function addEducation() {
    try {
      await apiClient("/api/v1/profile/education", {
        method: "POST",
        body: JSON.stringify({
          degree: newEducation.degree,
          institution: newEducation.institution,
          start_date: newEducation.start_date || null,
          end_date: newEducation.end_date || null,
          status: newEducation.status || null,
        }),
      });
      setNewEducation(emptyEducation);
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add education");
    }
  }

  async function deleteEducation(id: string) {
    try {
      await apiClient(`/api/v1/profile/education/${id}`, { method: "DELETE" });
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove education");
    }
  }

  async function addCertification() {
    try {
      await apiClient("/api/v1/profile/certifications", {
        method: "POST",
        body: JSON.stringify({
          name: newCertification.name,
          issuer: newCertification.issuer,
          issued_at: newCertification.issued_at || null,
          expires_at: newCertification.expires_at || null,
        }),
      });
      setNewCertification(emptyCertification);
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add certification");
    }
  }

  async function deleteCertification(id: string) {
    try {
      await apiClient(`/api/v1/profile/certifications/${id}`, { method: "DELETE" });
      await loadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove certification");
    }
  }

  function handleCVFileSelect(file: File) {
    if (!file.type.includes("pdf") && !file.name.endsWith(".docx")) {
      setCvError("Please upload a PDF or DOCX file");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setCvError("File size must be less than 5 MB");
      return;
    }

    setCvFileName(file.name);
    setCvError(null);
  }

  async function handleCVUpload() {
    if (!cvFileInputRef.current?.files?.[0]) {
      setCvError("Please select a file");
      return;
    }

    const file = cvFileInputRef.current.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      setCvUploadStatus("uploading");
      setCvError(null);

      const formData = new FormData();
      formData.append("file", file);

      await uploadFile("/api/v1/profile/cv", formData);

      setCvUploadStatus("success");
      setCvFileName(null);
      if (cvFileInputRef.current) {
          cvFileInputRef.current.value = "";
        }
        setTimeout(() => {
          fetchCV();
          setCvUploadStatus("idle");
        }, 1500);
    } catch (err) {
      let errorMsg = "Upload failed";
      if (err instanceof Error) {
        if (err.message.includes("413")) {
          errorMsg = "File is too large (max 5 MB)";
        } else if (err.message.includes("401")) {
          errorMsg = "Session expired";
        } else {
          errorMsg = err.message;
        }
      }
      setCvError(errorMsg);
      setCvUploadStatus("error");
    }
  }

  async function deleteCurrentCV() {
    try {
      setCvDeleteStatus("deleting");
      setCvError(null);
      await apiClient("/api/v1/profile/cv", { method: "DELETE" });
      setCurrentCV(null);
      setMessage("CV deleted");
    } catch (err) {
      setCvDeleteStatus("error");
      setCvError(err instanceof Error ? err.message : "Failed to delete CV");
      return;
    }

    setCvDeleteStatus("idle");
  }

  if (loading) {
    return <div className="animate-pulse">Loading profile...</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Profile Management</h1>
        <p className="text-sm text-muted mt-2">Manage all profile sections connected to gateway and microservices.</p>
      </div>

      {error ? <div className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div> : null}
      {message ? <div className="rounded border border-green-200 bg-green-50 p-3 text-green-700">{message}</div> : null}

      <section className="rounded border border-primary/20 bg-surface p-4 space-y-3">
        <h2 className="font-semibold">Base Profile</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="border rounded p-2" placeholder="Full name" value={baseForm.full_name} onChange={(e) => setBaseForm((s) => ({ ...s, full_name: e.target.value }))} />
          <input className="border rounded p-2" placeholder="Headline" value={baseForm.headline} onChange={(e) => setBaseForm((s) => ({ ...s, headline: e.target.value }))} />
          <input className="border rounded p-2 md:col-span-2" placeholder="Summary" value={baseForm.summary} onChange={(e) => setBaseForm((s) => ({ ...s, summary: e.target.value }))} />
          <input className="border rounded p-2" placeholder="Legacy location" value={baseForm.location} onChange={(e) => setBaseForm((s) => ({ ...s, location: e.target.value }))} />
          <input className="border rounded p-2" placeholder="Years experience" value={baseForm.years_experience} onChange={(e) => setBaseForm((s) => ({ ...s, years_experience: e.target.value }))} />
          <select className="border rounded p-2" value={baseForm.work_mode_preference} onChange={(e) => setBaseForm((s) => ({ ...s, work_mode_preference: e.target.value }))}>
            <option value="">Work mode</option>
            <option value="remote">remote</option>
            <option value="hybrid">hybrid</option>
            <option value="onsite">onsite</option>
          </select>
          <select className="border rounded p-2" value={baseForm.country_code} onChange={(e) => setBaseForm((s) => ({ ...s, country_code: e.target.value, region_id: "", city_id: "" }))}>
            <option value="">Country</option>
            {countries.map((c) => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </select>
          <select
            className={`border rounded p-2 transition-opacity ${!baseForm.country_code ? "opacity-40 cursor-not-allowed bg-gray-50" : ""}`}
            disabled={!baseForm.country_code}
            value={baseForm.region_id}
            onChange={(e) => setBaseForm((s) => ({ ...s, region_id: e.target.value, city_id: "" }))}
          >
            <option value="">{baseForm.country_code ? "Region" : "Select a country first"}</option>
            {regions.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          <select
            className={`border rounded p-2 transition-opacity ${!baseForm.region_id ? "opacity-40 cursor-not-allowed bg-gray-50" : ""}`}
            disabled={!baseForm.region_id}
            value={baseForm.city_id}
            onChange={(e) => setBaseForm((s) => ({ ...s, city_id: e.target.value }))}
          >
            <option value="">{baseForm.region_id ? "City" : "Select a region first"}</option>
            {cities.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <button className="rounded bg-primary px-4 py-2 text-white" onClick={saveBaseProfile}>Save Base Profile</button>
      </section>

      <section className="rounded border border-primary/20 bg-surface p-4 space-y-3">
        <h2 className="font-semibold">Skills</h2>
        <div className="flex flex-wrap gap-2">
          {profile?.skills.map((s) => (
            <span key={s.skill_id} className="inline-flex items-center gap-2 rounded border px-2 py-1 text-sm">
              {s.label}
              <button className="text-red-600" onClick={() => removeSkill(s.skill_id)}>x</button>
            </span>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input list="skills-list" className="border rounded p-2" placeholder="Skill" value={newSkill.skill_name} onChange={(e) => { setSkillError(null); setNewSkill((s) => ({ ...s, skill_name: e.target.value })); }} />
          <datalist id="skills-list">
            {skillsCatalog.map((s) => (
              <option key={s.id} value={s.skill_name || ""} />
            ))}
          </datalist>
          <input className="border rounded p-2" placeholder="Proficiency (optional)" value={newSkill.proficiency_level} onChange={(e) => setNewSkill((s) => ({ ...s, proficiency_level: e.target.value }))} />
          <button className="rounded bg-primary px-4 py-2 text-white" onClick={addSkill}>Add Skill</button>
        </div>
        {skillError ? (
          <p className="text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            {skillError}
          </p>
        ) : null}
      </section>

      <section className="rounded border border-primary/20 bg-surface p-4 space-y-3">
        <h2 className="font-semibold">Preferred Roles</h2>
        <div className="flex flex-wrap gap-2">
          {profile?.preferred_roles.map((r) => (
            <span key={r.id} className="inline-flex items-center gap-2 rounded border px-2 py-1 text-sm">
              {r.role_name}
              <button className="text-red-600" onClick={() => deleteRole(r.id)}>x</button>
            </span>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <input list="roles-list" className="border rounded p-2" placeholder="Preferred role" value={newRole.role_name} onChange={(e) => { setRoleError(null); setNewRole({ role_name: e.target.value }); }} />
          <datalist id="roles-list">
            {rolesCatalog.map((r) => (
              <option key={r.id} value={r.role_name || ""} />
            ))}
          </datalist>
          <button className="rounded bg-primary px-4 py-2 text-white" onClick={addRole}>Add Role</button>
        </div>
        {roleError ? (
          <p className="text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            {roleError}
          </p>
        ) : null}
      </section>

      <section className="rounded border border-primary/20 bg-surface p-4 space-y-3">
        <h2 className="font-semibold">Experience</h2>
        <div className="space-y-2">
          {profile?.experience.map((x) => (
            <div key={x.id} className="rounded border p-2 flex items-center justify-between">
              <div>{x.position} at {x.company}</div>
              <button className="text-red-600" onClick={() => deleteExperience(x.id)}>Delete</button>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <input className="border rounded p-2" placeholder="Position" value={newExperience.position} onChange={(e) => setNewExperience((s) => ({ ...s, position: e.target.value }))} />
          <input className="border rounded p-2" placeholder="Company" value={newExperience.company} onChange={(e) => setNewExperience((s) => ({ ...s, company: e.target.value }))} />
          <input className="border rounded p-2" type="date" value={newExperience.start_date} onChange={(e) => setNewExperience((s) => ({ ...s, start_date: e.target.value }))} />
          <input className="border rounded p-2" type="date" value={newExperience.end_date} onChange={(e) => setNewExperience((s) => ({ ...s, end_date: e.target.value }))} />
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={newExperience.is_current} onChange={(e) => setNewExperience((s) => ({ ...s, is_current: e.target.checked }))} />Current role</label>
          <textarea className="border rounded p-2 md:col-span-2" placeholder="Responsibilities (one per line)" value={newExperience.responsibilities} onChange={(e) => setNewExperience((s) => ({ ...s, responsibilities: e.target.value }))} />
          <button className="rounded bg-primary px-4 py-2 text-white" onClick={addExperience}>Add Experience</button>
        </div>
      </section>

      <section className="rounded border border-primary/20 bg-surface p-4 space-y-3">
        <h2 className="font-semibold">Education</h2>
        <div className="space-y-2">
          {profile?.education.map((x) => (
            <div key={x.id} className="rounded border p-2 flex items-center justify-between">
              <div>{x.degree} at {x.institution}</div>
              <button className="text-red-600" onClick={() => deleteEducation(x.id)}>Delete</button>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <input
            list="degree-types-list"
            className="border rounded p-2"
            placeholder="Degree"
            value={newEducation.degree}
            onChange={(e) => setNewEducation((s) => ({ ...s, degree: e.target.value }))}
          />
          <datalist id="degree-types-list">
            {degreeTypesCatalog.map((d) => (
              <option key={d.id} value={d.degree_name || ""} />
            ))}
          </datalist>
          <input className="border rounded p-2" placeholder="Institution" value={newEducation.institution} onChange={(e) => setNewEducation((s) => ({ ...s, institution: e.target.value }))} />
          <input className="border rounded p-2" type="date" value={newEducation.start_date} onChange={(e) => setNewEducation((s) => ({ ...s, start_date: e.target.value }))} />
          <input className="border rounded p-2" type="date" value={newEducation.end_date} onChange={(e) => setNewEducation((s) => ({ ...s, end_date: e.target.value }))} />
          <input className="border rounded p-2" placeholder="Status" value={newEducation.status} onChange={(e) => setNewEducation((s) => ({ ...s, status: e.target.value }))} />
          <button className="rounded bg-primary px-4 py-2 text-white" onClick={addEducation}>Add Education</button>
        </div>
      </section>

      <section className="rounded border border-primary/20 bg-surface p-4 space-y-3">
        <h2 className="font-semibold">Certifications</h2>
        <div className="space-y-2">
          {profile?.certifications.map((x) => (
            <div key={x.id} className="rounded border p-2 flex items-center justify-between">
              <div>{x.name} - {x.issuer}</div>
              <button className="text-red-600" onClick={() => deleteCertification(x.id)}>Delete</button>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <input className="border rounded p-2" placeholder="Certification name" value={newCertification.name} onChange={(e) => setNewCertification((s) => ({ ...s, name: e.target.value }))} />
          <input className="border rounded p-2" placeholder="Issuer" value={newCertification.issuer} onChange={(e) => setNewCertification((s) => ({ ...s, issuer: e.target.value }))} />
          <input className="border rounded p-2" type="date" value={newCertification.issued_at} onChange={(e) => setNewCertification((s) => ({ ...s, issued_at: e.target.value }))} />
          <input className="border rounded p-2" type="date" value={newCertification.expires_at} onChange={(e) => setNewCertification((s) => ({ ...s, expires_at: e.target.value }))} />
          <button className="rounded bg-primary px-4 py-2 text-white" onClick={addCertification}>Add Certification</button>
        </div>
      </section>

      <section className="rounded border border-primary/20 bg-surface p-4 space-y-3">
        <h2 className="font-semibold flex items-center gap-2">?? CV / Resume</h2>

        {/* Current CV Display */}
        {currentCV && (
          <div className="bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded p-4 space-y-3">
            <div className="flex items-start gap-3">
              <File className="w-6 h-6 text-green-700 flex-shrink-0 mt-1" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-foreground truncate">{currentCV.original_filename}</p>
                <p className="text-xs text-muted mt-1">
                  Uploaded: {new Date(currentCV.uploaded_at).toLocaleDateString()}
                  {currentCV.parse_status === "pending" && " ? Parsing..."}
                  {currentCV.parse_status === "completed" && " ? ? Parsed"}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <button className="flex items-center gap-1 text-sm px-3 py-1 bg-primary text-white rounded hover:bg-primary/90" onClick={() => { setCvFileName(null); if (cvFileInputRef.current) cvFileInputRef.current.value = ""; }}>
                <RefreshCw className="w-4 h-4" />
                Replace
              </button>
              <button
                type="button"
                disabled={cvDeleteStatus === "deleting"}
                className="flex items-center gap-1 text-sm px-3 py-1 border border-red-200 text-red-600 rounded hover:bg-red-50 disabled:opacity-60 disabled:cursor-not-allowed"
                onClick={() => void deleteCurrentCV()}
              >
                <Trash2 className="w-4 h-4" />
                {cvDeleteStatus === "deleting" ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        )}

        {/* Upload Area */}
        {!currentCV && (
          <div className="space-y-2">
            <div className="border-2 border-dashed border-primary/20 rounded p-6 text-center">
              <input
                ref={cvFileInputRef}
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    handleCVFileSelect(e.target.files[0]);
                  }
                }}
                className="hidden"
              />

              {cvUploadStatus === "idle" && !cvFileName && (
                <div onClick={() => cvFileInputRef.current?.click()} className="cursor-pointer space-y-2">
                  <Upload className="w-8 h-8 text-primary mx-auto" />
                  <p className="font-medium text-foreground">Drag and drop or click to upload</p>
                  <p className="text-xs text-muted">PDF or DOCX, up to 5 MB</p>
                </div>
              )}

              {cvFileName && cvUploadStatus === "idle" && (
                <div className="space-y-2">
                  <File className="w-8 h-8 text-primary mx-auto" />
                  <p className="font-medium text-foreground">{cvFileName}</p>
                  <p className="text-xs text-muted">Ready to upload</p>
                </div>
              )}

              {cvUploadStatus === "uploading" && (
                <div className="space-y-2">
                  <div className="w-6 h-6 border-3 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="font-medium text-foreground">Uploading...</p>
                </div>
              )}

              {cvUploadStatus === "success" && (
                <div className="space-y-2">
                  <Check className="w-8 h-8 text-green-600 mx-auto" />
                  <p className="font-medium text-green-600">Upload successful!</p>
                </div>
              )}
            </div>

            {cvError && (
              <div className="bg-red-50 border border-red-200 rounded p-3 flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-red-700 text-sm">{cvError}</p>
              </div>
            )}

            {cvFileName && cvUploadStatus === "idle" && (
              <div className="flex gap-2">
                <button className="flex-1 rounded bg-primary px-4 py-2 text-white font-medium hover:bg-primary/90" onClick={handleCVUpload}>
                  Upload CV
                </button>
                <button
                  className="flex-1 rounded border border-primary/20 px-4 py-2 font-medium hover:bg-primary/5"
                  onClick={() => {
                    setCvFileName(null);
                    if (cvFileInputRef.current) {
                      cvFileInputRef.current.value = "";
                    }
                  }}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
