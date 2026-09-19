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

 limits: {
  cpu: string | null;
  memory: string | null;
  cpu_allowance: string | null;
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

export interface StoragePoolOption {
  name: string;
  driver: string;
  space: {
    total_bytes: number;
    used_bytes: number;
    available_bytes: number;
  };
  inodes: {
    total: number;
    used: number;
  };
}

export interface NetworkOption {
  name: string;
  type: string;
  managed: boolean;
}

export interface ContainerOptionsResponse {
  images: string[];
  networks: NetworkOption[];
  storage_pools: StoragePoolOption[];
}

export interface HostResourcesResponse {
  cpu: {
    logical_cpus: number;
    architecture: string | null;
  };
  memory: {
    total_bytes: number;
    used_bytes: number;
    available_bytes: number;
  };
}

export interface CreateContainerPayload {
  name: string;
  image: string;
  memory: string;
  cpu_cores: number;
  cpu_allowance: number;
  disk: string;
  storage_pool: string;
  network: string;
  owner_user_id?: number;
  ephemeral: boolean;
  autostart: boolean;
  description?: string;
}

export interface CreateContainerResponse {
  message: string;
  container: {
    id: number;
    lxd_uuid: string;
    lxd_name: string;
    description: string | null;
    owner_user_id: number | null;
    created_at: string;
    updated_at: string;
  };
}

export function getContainerOptions() {
  return apiJson<ContainerOptionsResponse>(
    "/api/container-options",
  );
}

export function getHostResources() {
  return apiJson<HostResourcesResponse>(
    "/api/host/resources",
  );
}

export function createContainer(
  payload: CreateContainerPayload,
) {
  return apiJson<CreateContainerResponse>(
    "/api/containers",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export interface UpdateContainerPayload {
  memory?: string;
  cpu_cores?: number;
  cpu_allowance?: number;
  disk?: string;
}

export interface UpdateContainerResponse {
  message: string;
  container: ContainerSummary;
}

export interface DeleteContainerResponse {
  message: string;
  container: {
    container_id: number;
    name: string;
    lxd_uuid: string;
    owner_user_id: number | null;
  };
}

export function updateContainer(
  containerId: number,
  payload: UpdateContainerPayload,
) {
  return apiJson<UpdateContainerResponse>(
    `/api/containers/${containerId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export function deleteContainer(
  containerId: number,
  confirmName: string,
) {
  return apiJson<DeleteContainerResponse>(
    `/api/containers/${containerId}`,
    {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        confirm_name: confirmName,
      }),
    },
  );
}

export interface InviteUserPayload {
  email: string;
  name?: string;
  role: "admin" | "container_user";
  ram_quota_bytes: number;
  cpu_quota: number;
  disk_quota_bytes: number;
}

export interface UpdateUserPayload {
  name?: string;
  role?: "admin" | "container_user";
  ram_quota_bytes?: number;
  cpu_quota?: number;
  disk_quota_bytes?: number;
}

export interface UserResponse {
  message: string;
  user: UserRecord;
}

export interface AssignedContainer {
  id: number;
  lxd_uuid: string;
  lxd_name: string;
  description: string | null;
  owner_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface UserAssignmentsResponse {
  user_id: number;
  containers: AssignedContainer[];
  count: number;
}

export function inviteUser(
  payload: InviteUserPayload,
) {
  return apiJson<UserResponse>(
    "/api/users",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export function updateUser(
  userId: number,
  payload: UpdateUserPayload,
) {
  return apiJson<UserResponse>(
    `/api/users/${userId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export function revokeUser(
  userId: number,
) {
  return apiJson<UserResponse>(
    `/api/users/${userId}`,
    {
      method: "DELETE",
    },
  );
}

export function getUserAssignments(
  userId: number,
) {
  return apiJson<UserAssignmentsResponse>(
    `/api/users/${userId}/containers`,
  );
}

export function assignContainerToUser(
  userId: number,
  containerId: number,
) {
  return apiJson(
    `/api/users/${userId}/containers/${containerId}`,
    {
      method: "PUT",
    },
  );
}

export function unassignContainerFromUser(
  userId: number,
  containerId: number,
) {
  return apiJson(
    `/api/users/${userId}/containers/${containerId}`,
    {
      method: "DELETE",
    },
  );
}
