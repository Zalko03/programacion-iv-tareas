const API_URL = "http://127.0.0.1:8000/api";
let accessToken = sessionStorage.getItem("accessToken") || null;
let currentProject = null;
let projectSocket = null;
let nextUrl = null;
let prevUrl = null;

function authHeaders() {
  return { Authorization: `Bearer ${accessToken}` };
}

async function login() {
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  const response = await fetch(`${API_URL}/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    document.getElementById("login-error").textContent =
      response.status === 429
        ? "Demasiados intentos. Esperen un minuto."
        : "Usuario o contraseña incorrectos.";
    return;
  }
  const data = await response.json();
  accessToken = data.access;
  sessionStorage.setItem("accessToken", accessToken);
  showApp();
}

function logout() {
  accessToken = null;
  sessionStorage.removeItem("accessToken");
  if (projectSocket) {
    projectSocket.close();
    projectSocket = null;
  }
  document.getElementById("login-box").style.display = "block";
  document.getElementById("app-box").style.display = "none";
  document.getElementById("username").value = "";
  document.getElementById("password").value = "";
}

function showApp() {
  document.getElementById("login-box").style.display = "none";
  document.getElementById("app-box").style.display = "block";
  loadProjects();
}

async function loadProjects() {
  const response = await fetch(`${API_URL}/projects/`, { headers: authHeaders() });
  if (response.status === 401) {
    logout();
    return;
  }
  const data = await response.json();
  const select = document.getElementById("project");
  select.innerHTML = "";
  data.results.forEach((project) => {
    const option = document.createElement("option");
    option.value = project.id;
    option.textContent = project.name;
    select.appendChild(option);
  });
  if (data.results.length > 0) {
    currentProject = data.results[0].id;
    select.value = currentProject;
    connectWebSocket(currentProject);
  }
  loadTasks();
}

function onProjectChange() {
  const select = document.getElementById("project");
  currentProject = select.value;
  connectWebSocket(currentProject);
}

function connectWebSocket(projectId) {
  if (projectSocket) {
    projectSocket.close();
  }
  if (!projectId || !accessToken) return;
  const wsUrl = `ws://127.0.0.1:8000/ws/projects/${projectId}/?token=${accessToken}`;
  projectSocket = new WebSocket(wsUrl);

  const statusEl = document.getElementById("ws-status");
  projectSocket.onopen = () => {
    statusEl.textContent = "Conectado en tiempo real al proyecto";
  };
  projectSocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.event === "task_created" || data.event === "task_updated" || data.event === "task_completed") {
        loadTasks();
      }
    } catch (e) {
      console.error("Error parsing WS message:", e);
    }
  };
  projectSocket.onclose = () => {
    statusEl.textContent = "";
  };
}

async function loadTasks(url = `${API_URL}/tasks/`) {
  const response = await fetch(url, { headers: authHeaders() });
  if (response.status === 401) {
    logout();
    return;
  }
  const data = await response.json();
  const list = document.getElementById("tasks");
  list.innerHTML = "";
  data.results.forEach((task) => {
    const li = document.createElement("li");
    li.textContent = `${task.title} - ${task.status}`;
    list.appendChild(li);
  });

  nextUrl = data.next;
  prevUrl = data.previous;
  document.getElementById("btn-next").disabled = !nextUrl;
  document.getElementById("btn-prev").disabled = !prevUrl;
}

function nextPage() {
  if (nextUrl) loadTasks(nextUrl);
}

function prevPage() {
  if (prevUrl) loadTasks(prevUrl);
}

async function createTask() {
  const titleInput = document.getElementById("new-title");
  const title = titleInput.value.trim();
  const project = document.getElementById("project").value;
  const errorBox = document.getElementById("app-error");
  errorBox.textContent = "";
  if (!title || !project) return;
  const response = await fetch(`${API_URL}/tasks/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title, project: Number(project) }),
  });
  if (!response.ok) {
    const data = await response.json();
    errorBox.textContent = data.detail ? JSON.stringify(data.detail) : "Error al crear la tarea.";
    return;
  }
  titleInput.value = "";
  loadTasks();
}

// Auto-login si ya existe token
if (accessToken) {
  showApp();
}
