/**
 * Centralized API client for all backend requests.
 * 
 * Usage:
 *   const data = await apiClient("/api/v1/profile");
 *   const result = await apiClient("/api/v1/profile/skills", { method: "POST", body: {...} });
 *   
 * For file uploads:
 *   const formData = new FormData();
 *   formData.append("file", fileInput.files[0]);
 *   const result = await uploadFile("/api/v1/profile/cv", formData);
 */

export async function apiClient(path: string, options?: RequestInit) {
  const url = path.startsWith("/api/") ? path : `/api/v1${path.startsWith("/") ? path : `/${path}`}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({ detail: "Request failed" }));
    const errorMessage = typeof payload === "object" && payload !== null && "detail" in payload 
      ? String(payload.detail) 
      : `HTTP ${res.status}`;
    throw new Error(errorMessage);
  }

  // Handle 204 No Content (DELETE responses)
  if (res.status === 204) {
    return null;
  }

  return res.json();
}

/**
 * Upload files to the API.
 * Do NOT set Content-Type header?the browser will set it automatically for FormData.
 */
export async function uploadFile(path: string, formData: FormData, options?: Omit<RequestInit, "body" | "headers">) {
  const url = path.startsWith("/api/") ? path : `/api/v1${path.startsWith("/") ? path : `/${path}`}`;

  const res = await fetch(url, {
    method: "POST",
    ...options,
    body: formData,
    // Note: Do NOT set Content-Type header for FormData
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({ detail: "Request failed" }));
    const errorMessage = typeof payload === "object" && payload !== null && "detail" in payload 
      ? String(payload.detail) 
      : `HTTP ${res.status}`;
    throw new Error(errorMessage);
  }

  return res.json();
}
