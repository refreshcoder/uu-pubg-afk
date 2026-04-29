function fmtRemaining(sec) {
  if (sec == null) return ""
  const s = Math.max(0, parseInt(sec, 10))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  const parts = []
  if (h) parts.push(`${h}h`)
  if (m || h) parts.push(`${m}m`)
  parts.push(`${r}s`)
  return parts.join(" ")
}

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  })
  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = null }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || text || `HTTP ${res.status}`
    throw new Error(msg)
  }
  return data
}

async function startDevice(key) {
  const hours = parseInt(prompt("运行小时数（0-999）", "6") || "0", 10)
  const minutes = parseInt(prompt("运行分钟数（0-59）", "5") || "0", 10)
  await api(`/api/devices/${encodeURIComponent(key)}/start`, {
    method: "POST",
    body: JSON.stringify({ hours, minutes }),
  })
  location.reload()
}

async function stopDevice(key) {
  await api(`/api/devices/${encodeURIComponent(key)}/stop`, { method: "POST" })
  location.reload()
}

async function deleteDevice(key) {
  if (!confirm("确认删除该设备？（必须先停止运行）")) return
  await api(`/api/devices/${encodeURIComponent(key)}`, { method: "DELETE" })
  location.href = "/"
}

async function saveDevice(key) {
  const form = document.querySelector("form[data-device-form]")
  const payload = {
    name: form.querySelector("[name=name]").value.trim(),
    target_id: form.querySelector("[name=target_id]").value.trim(),
    target_password: form.querySelector("[name=target_password]").value,
    display: form.querySelector("[name=display]").value.trim() || ":99",
    override_config_yaml: form.querySelector("[name=override_config_yaml]").value,
    note: form.querySelector("[name=note]").value,
  }
  if (!payload.name || !payload.target_id || !payload.target_password) {
    alert("请填写：设备名称 / 远控ID / 远控密码")
    return
  }
  if (key) {
    await api(`/api/devices/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify(payload) })
    location.href = `/devices/${encodeURIComponent(key)}`
  } else {
    const res = await api("/api/devices", { method: "POST", body: JSON.stringify(payload) })
    const newKey = res.device.key
    location.href = `/devices/${encodeURIComponent(newKey)}`
  }
}

window.PUBG_AFK_UI = { startDevice, stopDevice, deleteDevice, saveDevice, fmtRemaining }

