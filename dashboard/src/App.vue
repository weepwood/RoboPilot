<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import ROSLIB from 'roslib'

const rosUrl = ref(localStorage.getItem('robopilot.rosUrl') || 'ws://localhost:9090')
const connectionState = ref('disconnected')
const connectionError = ref('')
const linearLimit = ref(0.45)
const angularLimit = ref(1.2)
const emergencyStopped = ref(false)
const activeMotion = ref(null)
const scanCanvas = ref(null)

const telemetry = ref({
  x: 0,
  y: 0,
  yaw: 0,
  linear: 0,
  angular: 0,
  scanCount: 0,
  nearestObstacle: null,
})

let ros = null
let cmdVelTopic = null
let odomTopic = null
let scanTopic = null
let publishTimer = null
let lastScan = null

const isConnected = computed(() => connectionState.value === 'connected')
const statusLabel = computed(() => {
  if (connectionState.value === 'connecting') return 'Connecting'
  if (connectionState.value === 'connected') return 'Connected'
  if (connectionState.value === 'error') return 'Connection error'
  return 'Disconnected'
})

function connect() {
  disconnect(false)
  connectionState.value = 'connecting'
  connectionError.value = ''
  localStorage.setItem('robopilot.rosUrl', rosUrl.value)

  ros = new ROSLIB.Ros({ url: rosUrl.value })

  ros.on('connection', () => {
    connectionState.value = 'connected'
    setupTopics()
  })

  ros.on('error', (error) => {
    connectionState.value = 'error'
    connectionError.value = error?.message || 'Unable to connect to rosbridge.'
    stopMotion()
  })

  ros.on('close', () => {
    connectionState.value = 'disconnected'
    stopMotion()
  })
}

function disconnect(closeSocket = true) {
  stopMotion()
  unsubscribeTopics()
  if (closeSocket && ros) ros.close()
  ros = null
  connectionState.value = 'disconnected'
}

function setupTopics() {
  cmdVelTopic = new ROSLIB.Topic({
    ros,
    name: '/cmd_vel',
    messageType: 'geometry_msgs/msg/Twist',
    queue_size: 1,
  })

  odomTopic = new ROSLIB.Topic({
    ros,
    name: '/odom',
    messageType: 'nav_msgs/msg/Odometry',
    throttle_rate: 100,
  })

  scanTopic = new ROSLIB.Topic({
    ros,
    name: '/scan',
    messageType: 'sensor_msgs/msg/LaserScan',
    throttle_rate: 100,
  })

  odomTopic.subscribe((message) => {
    const pose = message.pose.pose
    const twist = message.twist.twist
    telemetry.value.x = Number(pose.position.x || 0)
    telemetry.value.y = Number(pose.position.y || 0)
    telemetry.value.yaw = quaternionToYaw(pose.orientation)
    telemetry.value.linear = Number(twist.linear.x || 0)
    telemetry.value.angular = Number(twist.angular.z || 0)
  })

  scanTopic.subscribe((message) => {
    lastScan = message
    const valid = message.ranges.filter((range) => Number.isFinite(range) && range >= message.range_min)
    telemetry.value.scanCount = valid.length
    telemetry.value.nearestObstacle = valid.length ? Math.min(...valid) : null
    nextTick(drawScan)
  })
}

function unsubscribeTopics() {
  odomTopic?.unsubscribe()
  scanTopic?.unsubscribe()
  odomTopic = null
  scanTopic = null
  cmdVelTopic = null
}

function quaternionToYaw(q) {
  const siny = 2 * (q.w * q.z + q.x * q.y)
  const cosy = 1 - 2 * (q.y * q.y + q.z * q.z)
  return Math.atan2(siny, cosy)
}

function commandFor(motion) {
  const linear = linearLimit.value
  const angular = angularLimit.value
  const commands = {
    forward: { linear: linear, angular: 0 },
    backward: { linear: -linear, angular: 0 },
    left: { linear: 0, angular: angular },
    right: { linear: 0, angular: -angular },
  }
  return commands[motion] || { linear: 0, angular: 0 }
}

function publishVelocity(linear = 0, angular = 0) {
  if (!cmdVelTopic || !isConnected.value) return
  cmdVelTopic.publish(
    new ROSLIB.Message({
      linear: { x: linear, y: 0, z: 0 },
      angular: { x: 0, y: 0, z: angular },
    }),
  )
}

function startMotion(motion) {
  if (!isConnected.value || emergencyStopped.value) return
  activeMotion.value = motion
  publishActiveMotion()
  clearInterval(publishTimer)
  publishTimer = window.setInterval(publishActiveMotion, 100)
}

function publishActiveMotion() {
  if (!activeMotion.value || emergencyStopped.value) return
  const command = commandFor(activeMotion.value)
  publishVelocity(command.linear, command.angular)
}

function stopMotion() {
  activeMotion.value = null
  clearInterval(publishTimer)
  publishTimer = null
  publishVelocity(0, 0)
}

function emergencyStop() {
  emergencyStopped.value = true
  stopMotion()
}

function resetEmergencyStop() {
  emergencyStopped.value = false
  stopMotion()
}

const keyboardMap = {
  w: 'forward',
  ArrowUp: 'forward',
  s: 'backward',
  ArrowDown: 'backward',
  a: 'left',
  ArrowLeft: 'left',
  d: 'right',
  ArrowRight: 'right',
}

function onKeyDown(event) {
  if (event.repeat) return
  if (event.code === 'Space') {
    event.preventDefault()
    stopMotion()
    return
  }
  const motion = keyboardMap[event.key]
  if (motion) {
    event.preventDefault()
    startMotion(motion)
  }
}

function onKeyUp(event) {
  if (keyboardMap[event.key] && activeMotion.value === keyboardMap[event.key]) {
    stopMotion()
  }
}

function drawScan() {
  const canvas = scanCanvas.value
  if (!canvas || !lastScan) return

  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  const width = Math.max(320, rect.width)
  const height = Math.max(280, rect.height)
  canvas.width = width * dpr
  canvas.height = height * dpr

  const context = canvas.getContext('2d')
  context.setTransform(dpr, 0, 0, dpr, 0, 0)
  context.clearRect(0, 0, width, height)

  const centerX = width / 2
  const centerY = height / 2
  const radius = Math.min(width, height) * 0.42
  const displayRange = Math.min(lastScan.range_max || 10, 10)

  context.strokeStyle = 'rgba(126, 150, 184, 0.18)'
  context.lineWidth = 1
  for (let ring = 1; ring <= 4; ring += 1) {
    context.beginPath()
    context.arc(centerX, centerY, (radius * ring) / 4, 0, Math.PI * 2)
    context.stroke()
  }

  context.beginPath()
  context.moveTo(centerX - radius, centerY)
  context.lineTo(centerX + radius, centerY)
  context.moveTo(centerX, centerY - radius)
  context.lineTo(centerX, centerY + radius)
  context.stroke()

  context.fillStyle = '#5fb8ff'
  for (let index = 0; index < lastScan.ranges.length; index += 2) {
    const range = lastScan.ranges[index]
    if (!Number.isFinite(range) || range < lastScan.range_min || range > displayRange) continue
    const angle = lastScan.angle_min + index * lastScan.angle_increment
    const scaled = (range / displayRange) * radius
    const x = centerX + Math.cos(angle) * scaled
    const y = centerY - Math.sin(angle) * scaled
    context.fillRect(x - 1, y - 1, 2, 2)
  }

  context.save()
  context.translate(centerX, centerY)
  context.rotate(-telemetry.value.yaw)
  context.fillStyle = '#ff6b4a'
  context.beginPath()
  context.moveTo(12, 0)
  context.lineTo(-8, -7)
  context.lineTo(-8, 7)
  context.closePath()
  context.fill()
  context.restore()
}

function format(value, digits = 2) {
  return Number(value || 0).toFixed(digits)
}

function handleVisibilityChange() {
  if (document.hidden) stopMotion()
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
  window.addEventListener('blur', stopMotion)
  window.addEventListener('resize', drawScan)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  connect()
})

onBeforeUnmount(() => {
  stopMotion()
  disconnect()
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
  window.removeEventListener('blur', stopMotion)
  window.removeEventListener('resize', drawScan)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">RP</div>
        <div>
          <p class="eyebrow">ROS 2 SIMULATION</p>
          <h1>RoboPilot Control Center</h1>
        </div>
      </div>
      <div class="connection-badge" :class="connectionState">
        <span class="status-dot"></span>
        {{ statusLabel }}
      </div>
    </header>

    <section class="connection-panel panel">
      <div>
        <label for="ros-url">Rosbridge WebSocket</label>
        <div class="connection-form">
          <input id="ros-url" v-model="rosUrl" type="text" spellcheck="false" />
          <button class="secondary" type="button" @click="connect">Connect</button>
          <button class="ghost" type="button" @click="disconnect">Disconnect</button>
        </div>
        <p v-if="connectionError" class="error-message">{{ connectionError }}</p>
      </div>
      <div class="safety-state" :class="{ stopped: emergencyStopped }">
        <span>{{ emergencyStopped ? 'E-STOP LATCHED' : 'DRIVE ENABLED' }}</span>
      </div>
    </section>

    <section class="dashboard-grid">
      <article class="panel drive-panel">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">MANUAL DRIVE</p>
            <h2>Velocity control</h2>
          </div>
          <span class="hint">W A S D · arrows · space</span>
        </div>

        <div class="drive-layout">
          <div class="dpad" :class="{ disabled: !isConnected || emergencyStopped }">
            <button class="drive-button forward" type="button" aria-label="Move forward" @pointerdown.prevent="startMotion('forward')" @pointerup="stopMotion" @pointerleave="stopMotion" @pointercancel="stopMotion">↑</button>
            <button class="drive-button left" type="button" aria-label="Turn left" @pointerdown.prevent="startMotion('left')" @pointerup="stopMotion" @pointerleave="stopMotion" @pointercancel="stopMotion">←</button>
            <button class="drive-button stop" type="button" aria-label="Stop" @click="stopMotion">■</button>
            <button class="drive-button right" type="button" aria-label="Turn right" @pointerdown.prevent="startMotion('right')" @pointerup="stopMotion" @pointerleave="stopMotion" @pointercancel="stopMotion">→</button>
            <button class="drive-button backward" type="button" aria-label="Move backward" @pointerdown.prevent="startMotion('backward')" @pointerup="stopMotion" @pointerleave="stopMotion" @pointercancel="stopMotion">↓</button>
          </div>

          <div class="limits">
            <label>
              <span>Linear limit <strong>{{ format(linearLimit) }} m/s</strong></span>
              <input v-model.number="linearLimit" type="range" min="0.1" max="1.0" step="0.05" />
            </label>
            <label>
              <span>Angular limit <strong>{{ format(angularLimit) }} rad/s</strong></span>
              <input v-model.number="angularLimit" type="range" min="0.3" max="2.5" step="0.1" />
            </label>
            <div class="safety-actions">
              <button class="emergency" type="button" @click="emergencyStop">E-STOP</button>
              <button class="secondary" type="button" :disabled="!emergencyStopped" @click="resetEmergencyStop">Reset</button>
            </div>
          </div>
        </div>
      </article>

      <article class="panel telemetry-panel">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">ODOMETRY</p>
            <h2>Robot state</h2>
          </div>
        </div>
        <div class="metric-grid">
          <div class="metric"><span>X position</span><strong>{{ format(telemetry.x) }} m</strong></div>
          <div class="metric"><span>Y position</span><strong>{{ format(telemetry.y) }} m</strong></div>
          <div class="metric"><span>Heading</span><strong>{{ format(telemetry.yaw * 180 / Math.PI, 1) }}°</strong></div>
          <div class="metric"><span>Linear speed</span><strong>{{ format(telemetry.linear) }} m/s</strong></div>
          <div class="metric"><span>Angular speed</span><strong>{{ format(telemetry.angular) }} rad/s</strong></div>
          <div class="metric"><span>Nearest object</span><strong>{{ telemetry.nearestObstacle === null ? '—' : `${format(telemetry.nearestObstacle)} m` }}</strong></div>
        </div>
      </article>

      <article class="panel lidar-panel">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">2D LIDAR</p>
            <h2>Live scan</h2>
          </div>
          <span class="hint">{{ telemetry.scanCount }} valid points</span>
        </div>
        <canvas ref="scanCanvas" aria-label="Lidar scan visualization"></canvas>
      </article>

      <article class="panel checklist-panel">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">STARTUP CHECK</p>
            <h2>System readiness</h2>
          </div>
        </div>
        <ul class="checklist">
          <li :class="{ ready: isConnected }"><span></span>Rosbridge connection</li>
          <li :class="{ ready: telemetry.scanCount > 0 }"><span></span>Lidar data stream</li>
          <li :class="{ ready: isConnected }"><span></span>Velocity command publisher</li>
          <li :class="{ ready: !emergencyStopped }"><span></span>Emergency stop released</li>
        </ul>
        <p class="note">Controls use a dead-man pattern. Releasing a key or button, hiding the page, or losing focus commands zero velocity.</p>
      </article>
    </section>
  </main>
</template>
