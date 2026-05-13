---
title: Windows Process & Network Tools — netstat, tasklist, taskkill, wmic
type: lesson
last_updated: 2026-05-13
---

# Windows Process & Network Tools

A working guide to the four Windows command-line tools you reach for when something is wrong with a process or a port: `netstat`, `tasklist`, `taskkill`, and `wmic`. Most of the time these come up together — you start at a port, follow it to a PID, follow the PID to a command line, and (sometimes) kill it.

---

## The mental model

Three pieces of vocabulary you need before the commands make sense.

**Process.** A running program. Each process has a unique numeric identifier — the **PID** (Process ID). When a program starts it gets a PID; when it exits the PID is freed and may later be reused for something else. The same `.exe` can be running multiple times, each with a different PID.

**Port.** A 16-bit number (0–65535) that lets multiple network services share one IP address. A web server binds to a port (e.g. 5000) and the OS routes incoming TCP packets to that port's owner. Most useful ports for development:
- `80` / `443` — HTTP / HTTPS
- `3000`, `5000`, `5173`, `8000`, `8080` — common dev-server defaults
- `5432` — Postgres
- `6379` — Redis

**TCP state.** A TCP connection has a lifecycle. The states you'll see in `netstat` output:
- `LISTENING` — a process is waiting for incoming connections on this port. This is what you look for when asking "who owns port 5000?"
- `ESTABLISHED` — an active in-flight connection.
- `TIME_WAIT` — the connection was just closed; the OS holds the slot for ~30s–2min to absorb any straggling packets. **TIME_WAIT entries are dead connections.** They cannot block a new server from binding. Ignore them when port-hunting.
- `CLOSE_WAIT` — the remote closed but the local app hasn't released its socket yet. Often a bug.

---

## netstat — who's listening on what port

`netstat` prints the OS's TCP/UDP connection table. The flags worth knowing:

| Flag | Meaning |
|------|---------|
| `-a` | All connections AND listening ports (default omits listeners) |
| `-n` | Show numeric addresses (no DNS lookup — much faster) |
| `-o` | Include the owning **PID** in each row |
| `-p tcp` | TCP only (skip UDP noise) |

The combo you'll use 90% of the time: **`netstat -ano`** — all sockets, numeric, with PIDs.

### Examples

**"What's on port 5000?"**
```bash
netstat -ano | findstr :5000
```
Look for rows in `LISTENING` state. The last column is the PID.

**"Show me only the listening servers, not active connections":**
```bash
netstat -ano | findstr LISTENING
```

**"Is anything talking to my database?":**
```bash
netstat -ano | findstr :5432
```

### Reading the output

```
TCP    0.0.0.0:5000    0.0.0.0:0    LISTENING    14868
```

- `0.0.0.0:5000` — local address. `0.0.0.0` means "all interfaces" (bound to every network adapter). `127.0.0.1:5000` would mean localhost-only.
- `0.0.0.0:0` — remote address. For a listener there's no remote yet, so it's zero.
- `LISTENING` — state.
- `14868` — PID of the owning process.

If you see **two `LISTENING` rows for the same port with different PIDs**, you have two processes that both think they own the port. On Windows with `SO_REUSEADDR` enabled (Werkzeug debug mode does this), this is legal but confusing — incoming requests go to one of them, effectively at random. This is a common cause of "I restarted my server but it's still serving the old code."

---

## tasklist — what process is PID N

Once `netstat` gives you a PID, `tasklist` tells you what that PID actually is.

### Examples

**"What is PID 14868?":**
```bash
tasklist /FI "PID eq 14868"
```
Output shows the image name (`python.exe`, `node.exe`, etc.), session, and memory use. The `/FI` flag is a filter — `"PID eq <n>"` is the syntax.

**"Show me every Python process":**
```bash
tasklist /FI "IMAGENAME eq python.exe"
```

**"All processes, with verbose info":**
```bash
tasklist /V
```

### Limitation

`tasklist` tells you the *executable* (`python.exe`) but not the *script* (`app.py` vs `admin_app.py`). For that you need `wmic`.

---

## wmic — the full command line of a process

`wmic` (Windows Management Instrumentation Command-line) exposes the entire WMI object model. It's overkill for most things, but it's the easiest way to ask **"what command line started this process?"** — which is exactly what you need to tell two `python.exe` instances apart.

> Note: `wmic` is deprecated in newer Windows 11 builds in favor of PowerShell's `Get-CimInstance`, but on Windows 10 it still works fine and is faster to type.

### Examples

**"What command launched PID 14868?":**
```bash
wmic process where "ProcessId=14868" get CommandLine
```
Returns the full command line, e.g. `python.exe admin_app.py` or `python.exe app.py`. This is how you confirm which entrypoint a Python process is actually running.

**"Show every Python process with its command line":**
```bash
wmic process where "name='python.exe'" get ProcessId,CommandLine
```

**"What's the parent process of PID 14868?":**
```bash
wmic process where "ProcessId=14868" get ParentProcessId
```
Useful for tracing process trees — e.g. Flask debug mode spawns a reloader child, and you can confirm which PID is the parent and which is the child.

### Syntax notes

- `where "..."` uses WQL (WMI Query Language). String values need single quotes inside the double-quoted clause.
- `get` selects which fields to return. Without it you get every field, which is unreadable.
- Multiple fields: `get ProcessId,Name,CommandLine` (no spaces after commas).

---

## taskkill — end a process

The blunt instrument. Once you've identified what you want to kill, this ends it.

### Examples

**"Kill PID 14868 (graceful)":**
```bash
taskkill /PID 14868
```
Sends a polite close request. The process can choose to ignore it.

**"Kill PID 14868 (force)":**
```bash
taskkill /PID 14868 /F
```
`/F` means force — equivalent to `kill -9` on Unix. The process gets no chance to clean up. Use when the graceful version doesn't work, or when you know the process is wedged.

**"Kill every python.exe (dangerous — kills *every* Python on the system)":**
```bash
taskkill /IM python.exe /F
```
`/IM` filters by image name. Useful when you've lost track of how many processes there are, but be careful — this includes Python processes you didn't start (e.g. a background script, an editor's language server).

**"Kill a process and all its children":**
```bash
taskkill /PID 14868 /T /F
```
`/T` (tree) walks the descendant processes too. Useful for killing a Flask debug server cleanly (parent + reloader child) in one shot.

---

## A real debugging workflow

The chain that started this lesson:

**1. Symptom:** Hitting `http://localhost:5000/admin` redirects to `/language-selection` even though `admin_app.py` should serve `/admin`.

**2. Find what's on the port:**
```bash
netstat -ano | findstr :5000
```
Reveals **two** `LISTENING` rows: PIDs `14868` and `17196`. Both processes are bound — incoming requests go to whichever one the OS picks.

**3. Identify the processes:**
```bash
wmic process where "ProcessId=14868" get CommandLine
wmic process where "ProcessId=17196" get CommandLine
```
One is `python.exe app.py` (left over from an earlier run), the other is `python.exe admin_app.py` (the one we just started). The old `app.py` is intercepting some of the requests — and `app.py` has no `/admin` route, so its 404 handler redirects to `/login`, which the login page's JS then turns into `/language-selection`.

**4. Kill the stale process:**
```bash
taskkill /PID 14868 /F
```

**5. Verify only one is left:**
```bash
netstat -ano | findstr :5000
```
Should now show one `LISTENING` row (plus harmless `TIME_WAIT` rows from previous client connections — those are not bindings, just connection-history bookkeeping).

**6. Confirm with the route:**
```bash
curl -i http://localhost:5000/admin
```
`HTTP/1.1 200 OK` — fixed.

---

## Quick reference

| Question | Command |
|----------|---------|
| What's listening on port N? | `netstat -ano \| findstr :N` |
| What is PID N? | `tasklist /FI "PID eq N"` |
| What command launched PID N? | `wmic process where "ProcessId=N" get CommandLine` |
| Show all instances of a program | `tasklist /FI "IMAGENAME eq name.exe"` |
| Kill PID N gracefully | `taskkill /PID N` |
| Kill PID N forcefully | `taskkill /PID N /F` |
| Kill PID N and all its children | `taskkill /PID N /T /F` |
| Kill every instance of a program | `taskkill /IM name.exe /F` |
| What's the parent process? | `wmic process where "ProcessId=N" get ParentProcessId` |

---

## Common pitfalls

- **`netstat` PIDs of `0`** mean "system" — the OS itself holds those connections (often `TIME_WAIT` slots). You can't and shouldn't kill PID 0.
- **`netstat` without `-n`** does DNS lookups and prints names like `localhost:http`. Slower and harder to grep. Always use `-n` for debugging.
- **`findstr` is case-sensitive by default.** Add `/I` if needed: `netstat -ano | findstr /I listening`.
- **TIME_WAIT entries are not the problem.** They show up after every closed connection and clear themselves in a couple of minutes. They cannot prevent a new server from binding.
- **Killing the Flask reloader's parent** without `/T` leaves an orphaned child still bound to the port. Use `/T` or kill both PIDs.
- **`wmic` requires admin for some queries** (mainly remote-machine ones); local-process inspection works without elevation.

---

## PowerShell equivalents

If you'd rather use PowerShell (more verbose but more composable):

| Task | PowerShell |
|------|------------|
| Listening sockets | `Get-NetTCPConnection -State Listen` |
| Process by PID | `Get-Process -Id 14868` |
| Command line of PID | `(Get-CimInstance Win32_Process -Filter "ProcessId=14868").CommandLine` |
| Kill PID | `Stop-Process -Id 14868 -Force` |

The PowerShell versions return objects (filterable with `Where-Object`, sortable, etc.) rather than text — useful when you want to script something instead of just typing one-off queries.
