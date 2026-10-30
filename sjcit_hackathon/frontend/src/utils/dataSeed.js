/**
 * dataSeed.js — Ensures IndexedDB is initialized and ready for offline use.
 *
 * On first app load, this opens the database (triggering schema creation)
 * so that all object stores exist before the user interacts with anything.
 * The actual question/explanation data comes from the catalog registry
 * which is bundled into the JS and always available offline.
 */
import { getAllProgressEvents } from '@/utils/indexedDB'

const SEED_VERSION_KEY = 'pragna-data-seed-version'
const CURRENT_SEED_VERSION = '2'

/**
 * Initializes the offline data layer. Safe to call on every app startup —
 * it's a no-op after the first successful run for each seed version.
 */
export async function seedOfflineData() {
  try {
    const existingVersion = localStorage.getItem(SEED_VERSION_KEY)
    if (existingVersion === CURRENT_SEED_VERSION) return

    // Trigger DB schema creation by reading from a store
    await getAllProgressEvents()

    localStorage.setItem(SEED_VERSION_KEY, CURRENT_SEED_VERSION)
    console.log(`[dataSeed] IndexedDB initialized for offline use (v${CURRENT_SEED_VERSION})`)
  } catch (error) {
    // Non-fatal — the app still works; DB will init on first interaction
    console.warn('[dataSeed] Could not initialize offline data:', error.message)
  }
}
