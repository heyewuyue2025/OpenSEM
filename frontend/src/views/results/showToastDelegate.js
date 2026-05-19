export function delegateShowToast({ msg, clearTimer, setTimer, setMessage, duration = 2200 }) {
  setMessage(msg)
  clearTimer()
  setTimer(() => {
    setMessage('')
    setTimer(null)
  }, duration)
}
