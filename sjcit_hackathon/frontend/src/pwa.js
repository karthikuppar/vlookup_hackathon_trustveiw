import { registerSW } from 'virtual:pwa-register'

registerSW({
  immediate: true,
  onRegisteredSW(_swUrl, registration) {
    registration?.update()
  },
  onNeedRefresh() {
    window.dispatchEvent(new CustomEvent('pwa-update-ready'))
  },
  onOfflineReady() {
    window.dispatchEvent(new CustomEvent('pwa-offline-ready'))
  },
})
