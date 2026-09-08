// Typed client for the Rust orchestration backend (backend/), which itself
// proxies to the Python scientific service (service/main.py). Candidate/mission
// payloads mirror service/schemas.py's Pydantic models field-for-field -- kept
// in sync by hand since Rust also treats them as opaque JSON (see
// backend/src/handlers.rs's module doc for why neither tier duplicates Python's
// domain schemas as its own source of truth).

const API_BASE = 'http://127.0.0.1:8080/api';

export interface ContinuousVariable {
	name: string;
	lower: number;
	upper: number;
	unit: string;
}

export interface DiscreteVariable {
	name: string;
	choices: string[];
}

export interface DesignSpace {
	continuous: ContinuousVariable[];
	discrete: DiscreteVariable[];
}

export interface CandidateSpec {
	battery_capacity_kwh: number;
	motor_power_kw: number;
	gear_ratio: number;
	drag_coefficient: number;
	frontal_area_m2: number;
	motor_architecture: string;
	battery_chemistry: string;
	num_motors: string;
	tire_choice: string;
}

export interface CostBreakdown {
	glider_usd: number;
	battery_usd: number;
	motor_usd: number;
	tire_delta_usd: number;
	total_usd: number;
}

export interface MassBreakdown {
	glider_kg: number;
	battery_kg: number;
	motor_kg: number;
	tire_delta_kg: number;
	total_kg: number;
}

export interface EvaluateResponse {
	vehicle_name: string;
	mass_kg: number;
	manufacturing_cost_usd: number;
	zero_to_sixty_s: number;
	range_mi: number;
	cost_breakdown: CostBreakdown;
	mass_breakdown: MassBreakdown;
}

export interface RequirementSpec {
	kind: string;
	threshold: number;
}

export interface ParetoPoint {
	candidate: CandidateSpec;
	objective_values: Record<string, number>;
}

export interface ParetoResult {
	n_points: number;
	points: ParetoPoint[];
}

export type ParetoJobStatus =
	| { status: 'running' }
	| { status: 'done'; result: ParetoResult }
	| { status: 'error'; message: string }
	| { status: 'not_found' };

async function parseErrorDetail(res: Response): Promise<string> {
	try {
		const body = await res.json();
		if (typeof body?.detail === 'string') return body.detail;
		return JSON.stringify(body);
	} catch {
		return `${res.status} ${res.statusText}`;
	}
}

export async function fetchDesignSpace(): Promise<DesignSpace> {
	const res = await fetch(`${API_BASE}/design-space`);
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export async function fetchRequirementKinds(): Promise<string[]> {
	const res = await fetch(`${API_BASE}/requirement-kinds`);
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export interface BenchmarkVehicle {
	name: string;
	epa_range_mi: number;
	msrp_usd: number;
	vehicle_type: string;
	drivetrain: string;
}

export async function fetchBenchmarkVehicles(): Promise<BenchmarkVehicle[]> {
	const res = await fetch(`${API_BASE}/benchmark-vehicles`);
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export interface SurrogateComparisonRow {
	target: string;
	gaussian_process: { r2: number; rmse: number; mae: number };
	random_forest: { r2: number; rmse: number; mae: number };
	selected_for_exploration: 'gaussian_process' | 'random_forest';
}

export interface SurrogateComparisonResponse {
	dataset: string;
	n_samples: number;
	seed: number;
	comparison: SurrogateComparisonRow[];
	selection_policy: string;
	claim_boundary: string;
}

export async function fetchSurrogateComparison(
	nSamples = 80,
	seed = 7
): Promise<SurrogateComparisonResponse> {
	const res = await fetch(`${API_BASE}/surrogate-comparison?n_samples=${nSamples}&seed=${seed}`);
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export async function fetchRobustRequirementKinds(): Promise<string[]> {
	const res = await fetch(`${API_BASE}/robust-requirement-kinds`);
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export interface RobustRequirementResult {
	name: string;
	unit: string;
	threshold: number;
	reliability_target: number;
	fraction_satisfied: number;
	satisfied: boolean;
	nominal_value: number;
	worst_value: number;
}

export interface RobustCheckResponse {
	robustly_feasible: boolean;
	n_samples: number;
	requirements: RobustRequirementResult[];
}

export async function checkRobustness(
	candidate: CandidateSpec,
	requirements: RequirementSpec[],
	nSamples: number,
	seed: number
): Promise<RobustCheckResponse> {
	const res = await fetch(`${API_BASE}/robust-check`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ candidate, requirements, n_samples: nSamples, seed })
	});
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export async function checkHealth(): Promise<{ status: string; python_service: string }> {
	const res = await fetch(`${API_BASE}/health`);
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export async function evaluateCandidate(candidate: CandidateSpec): Promise<EvaluateResponse> {
	const res = await fetch(`${API_BASE}/evaluate`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(candidate)
	});
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export async function startParetoJob(
	requirements: RequirementSpec[],
	popSize: number,
	nGen: number,
	seed: number
): Promise<string> {
	const res = await fetch(`${API_BASE}/pareto`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			mission: { name: 'workstation mission', requirements },
			pop_size: popSize,
			n_gen: nGen,
			seed
		})
	});
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	const body = await res.json();
	return body.job_id as string;
}

export async function pollParetoJob(jobId: string): Promise<ParetoJobStatus> {
	const res = await fetch(`${API_BASE}/pareto/${jobId}`);
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}

export interface AgentToolCallSummary {
	name: string;
	input: Record<string, unknown>;
	result: Record<string, unknown>;
	is_error: boolean;
}

export interface AgentChatResponse {
	final_text: string;
	tool_calls: AgentToolCallSummary[];
	hops_used: number;
	forced_final: boolean;
}

// Single-turn only, matching service/schemas.py's AgentChatRequest -- each call
// is a fresh agent run with no server-side memory of prior messages. The page
// keeps a local transcript purely for display; it isn't sent back to the agent.
export async function sendAgentMessage(message: string): Promise<AgentChatResponse> {
	const res = await fetch(`${API_BASE}/agent/chat`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ message })
	});
	if (!res.ok) throw new Error(await parseErrorDetail(res));
	return res.json();
}
