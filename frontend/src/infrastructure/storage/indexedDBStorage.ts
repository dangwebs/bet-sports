import localforage from "localforage";
import { StateStorage } from "zustand/middleware";

// Initialize localforage with a dedicated store for Zustand
localforage.config({
  name: "BJJ-BetSports",
  version: 1.0,
  storeName: "app_state",
  description:
    "Persistent storage for BJJ-BetSports application state using IndexedDB",
});

/**
 * Custom storage adapter for Zustand's persist middleware using localforage.
 * This provides significantly larger storage capacity (IndexedDB) than localStorage.
 */
export const indexedDBStorage: StateStorage = {
  getItem: async (name: string): Promise<string | null> => {
    try {
      const value = await localforage.getItem<any>(name);
      if (!value) return null;
      // Zustand expect a string, but localforage can store objects.
      // We stringify to maintain compatibility with Zustand's default JSON parser
      return JSON.stringify(value);
    } catch (error) {
      console.warn(`Error reading ${name} from IndexedDB:`, error);
      return null;
    }
  },
  setItem: async (name: string, value: string): Promise<void> => {
    try {
      // Parse the value before storing if you want to store objects directly in localforage,
      // but Zustand already stringifies for createJSONStorage.
      // So we just store it.
      await localforage.setItem(name, JSON.parse(value));
    } catch (error) {
      console.error(`Error saving ${name} to IndexedDB:`, error);
      // If IndexedDB fails (very rare compared to localStorage), we don't have many options,
      // but at least it won't crash the main execution if handled.
    }
  },
  removeItem: async (name: string): Promise<void> => {
    try {
      await localforage.removeItem(name);
    } catch (error) {
      console.warn(`Error removing ${name} from IndexedDB:`, error);
    }
  },
};
