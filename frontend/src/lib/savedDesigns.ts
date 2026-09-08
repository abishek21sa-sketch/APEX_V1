// Local-only persistence (localStorage, not a backend concept) for designs an
// engineer wants to keep around and compare later -- no server-side session
// or account system exists in this platform, so "saved" means "saved in this
// browser."

import type { CandidateSpec, EvaluateResponse } from './api';

const STORAGE_KEY = 'apex_saved_designs_v1';

export interface SavedDesign {
	id: string;
	savedAt: string;
	label: string;
	candidate: CandidateSpec;
	result: EvaluateResponse;
}

export function getSavedDesigns(): SavedDesign[] {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return [];
		return JSON.parse(raw) as SavedDesign[];
	} catch {
		return [];
	}
}

export function saveDesign(candidate: CandidateSpec, result: EvaluateResponse, label?: string): SavedDesign {
	const design: SavedDesign = {
		id: crypto.randomUUID(),
		savedAt: new Date().toISOString(),
		label: label?.trim() || result.vehicle_name,
		candidate,
		result
	};
	const existing = getSavedDesigns();
	localStorage.setItem(STORAGE_KEY, JSON.stringify([...existing, design]));
	return design;
}

export function removeSavedDesign(id: string): void {
	const remaining = getSavedDesigns().filter((d) => d.id !== id);
	localStorage.setItem(STORAGE_KEY, JSON.stringify(remaining));
}
