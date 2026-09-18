export type UserRole =
  | "admin"
  | "container_user";

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  ram_quota_bytes: number;
  cpu_quota: number;
  disk_quota_bytes: number;
}

export interface AuthResponse {
  authenticated: true;
  csrf_token: string;
  user: AuthUser;
}

export interface ContainerSummary {
  container_id: number | null;
  name: string;
  lxd_uuid?: string;
  status: string;
  type?: string;
  ipv4?: string | null;
  pid?: number | null;
  uptime_seconds?: number | null;
  processes?: number;

  image?: {
    os?: string;
    version?: string;
    release?: string;
    architecture?: string;
    description?: string;
  };

  limits?: {
    cpu?: string | null;
    memory?: string | null;
  };

  cpu?: {
    usage_ns?: number;
  };

  memory?: {
    used_bytes?: number;
    reported_total_bytes?: number;
    percent?: number | null;
  };

  disk?: {
    used_bytes?: number | null;
    allocated_bytes?: number | null;
    percent?: number | null;
    usage_source?: string | null;
  };

  network?: {
    rx_bytes?: number;
    tx_bytes?: number;
  };
}

export interface ContainersResponse {
  containers: ContainerSummary[];
  count: number;
}

export interface UserRecord {
  id: number;
  email: string;
  name: string | null;
  role: UserRole;
  invited: boolean;
  active: boolean;
  ram_quota_bytes: number;
  cpu_quota: number;
  disk_quota_bytes: number;
  created_at: string;
  updated_at: string;
}

export interface UsersResponse {
  users: UserRecord[];
  count: number;
}


/* -------------------------------------------------------------------------- */
/* Container detail / actions                                                  */
/* -------------------------------------------------------------------------- */

export interface ContainerDetailResponse {
  container_id: number;
  container: ContainerSummary;
}

export interface ActionResponse {
  message?: string;
  container?: ContainerSummary;
}


/* -------------------------------------------------------------------------- */
/* CSRF token                                                                  */
/* -------------------------------------------------------------------------- */

let csrfToken: string | null = null;


/* -------------------------------------------------------------------------- */
/* Error handling                                                              */
/* -------------------------------------------------------------------------- */

async function readError(
  response: Response,
): Promise<string> {
  try {
    const data = await response.json();

    if (
      data &&
      typeof data.error === "string"
    ) {
      return data.error;
    }
  } catch {
    // Ignore non-JSON error responses.
  }

  return `Request failed: ${response.status}`;
}


/* -------------------------------------------------------------------------- */
/* Authentication                                                              */
/* -------------------------------------------------------------------------- */

export async function getCurrentUser():
  Promise<AuthResponse | null> {
  const response = await fetch(
    "/api/auth/me",
    {
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (response.status === 401) {
    csrfToken = null;
    return null;
  }

  if (!response.ok) {
    throw new Error(
      await readError(response),
    );
  }

  const data =
    await response.json() as AuthResponse;

  csrfToken = data.csrf_token;

  return data;
}


/* -------------------------------------------------------------------------- */
/* API fetch                                                                   */
/* -------------------------------------------------------------------------- */

export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const method = (
    options.method ?? "GET"
  ).toUpperCase();

  const headers = new Headers(
    options.headers,
  );

  headers.set(
    "Accept",
    "application/json",
  );

  const mutatingMethods = new Set([
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
  ]);

  if (
    mutatingMethods.has(method)
    && !csrfToken
  ) {
    await getCurrentUser();
  }

  if (
    mutatingMethods.has(method)
    && csrfToken
  ) {
    headers.set(
      "X-CSRF-Token",
      csrfToken,
    );
  }

  return fetch(
    path,
    {
      ...options,
      method,
      headers,
      credentials: "same-origin",
    },
  );
}


/* -------------------------------------------------------------------------- */
/* JSON API helper                                                             */
/* -------------------------------------------------------------------------- */

export async function apiJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await apiFetch(
    path,
    options,
  );

  if (!response.ok) {
    throw new Error(
      await readError(response),
    );
  }

  return await response.json() as T;
}


/* -------------------------------------------------------------------------- */
/* Containers                                                                  */
/* -------------------------------------------------------------------------- */

export function getContainers() {
  return apiJson<ContainersResponse>(
    "/api/containers",
  );
}


export function getContainer(
  containerId: number,
) {
  return apiJson<ContainerDetailResponse>(
    `/api/containers/${containerId}`,
  );
}


export function runContainerAction(
  containerId: number,
  action: string,
) {
  return apiJson<ActionResponse>(
    `/api/containers/${containerId}/actions/${action}`,
    {
      method: "POST",
    },
  );
}


/* -------------------------------------------------------------------------- */
/* Users                                                                       */
/* -------------------------------------------------------------------------- */

export function getUsers() {
  return apiJson<UsersResponse>(
    "/api/users",
  );
}


/* -------------------------------------------------------------------------- */
/* Logout                                                                      */
/* -------------------------------------------------------------------------- */

export async function logout():
  Promise<void> {
  const response = await apiFetch(
    "/api/auth/logout",
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readError(response),
    );
  }

  csrfToken = null;
}
export interface MetricPoint {
  time: string;
  state: string | null;
  cpu_percent: number | null;
  uptime_seconds: number | null;
  memory_used_bytes: number | null;
  memory_limit_bytes: number | null;
  memory_percent: number | null;
  processes: number | null;
  rx_bytes: number | null;
  tx_bytes: number | null;
  rx_bytes_per_second: number | null;
  tx_bytes_per_second: number | null;
  disk_used_bytes: number | null;
  disk_allocated_bytes: number | null;
  disk_percent: number | null;
}

export interface MetricsResponse {
  container_id: number;
  container_name: string;
  hours: number;
  sample_count: number;
  returned_count: number;
  points: MetricPoint[];
}

export interface TerminalResponse {
  exit_code: number;
  stdout: string;
  stderr: string;
  truncated: boolean;
}

export function getContainerMetrics(
  containerId: number,
  hours = 6,
  maxPoints = 180,
) {
  return apiJson<MetricsResponse>(
    `/api/containers/${containerId}/metrics`
    + `?hours=${hours}`
    + `&max_points=${maxPoints}`,
  );
}

export function executeTerminalCommand(
  containerId: number,
  command: string,
) {
  return apiJson<TerminalResponse>(
    `/api/containers/${containerId}/terminal`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        command,
      }),
    },
  );
}
