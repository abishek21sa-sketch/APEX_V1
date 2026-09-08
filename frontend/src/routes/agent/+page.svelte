<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { sendAgentMessage, type AgentChatResponse } from '$lib/api';

	interface AgentExchange {
		question: string;
		response: AgentChatResponse | null;
		error: string | null;
	}
	let agentMessage = $state('');
	let agentLoading = $state(false);
	let agentExchanges = $state<AgentExchange[]>([]);

	function renderMarkdown(text: string): string {
		const html = marked.parse(text, { async: false }) as string;
		return DOMPurify.sanitize(html);
	}

	async function askAgent() {
		const question = agentMessage.trim();
		if (!question) return;
		agentMessage = '';
		agentLoading = true;
		const index = agentExchanges.length;
		agentExchanges = [...agentExchanges, { question, response: null, error: null }];
		try {
			const response = await sendAgentMessage(question);
			agentExchanges[index] = { question, response, error: null };
		} catch (e) {
			agentExchanges[index] = { question, response: null, error: e instanceof Error ? e.message : String(e) };
		} finally {
			agentLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Agent — APEX</title>
</svelte:head>

<div class="shell">
	<header class="page-header">
		<p class="eyebrow">Vehicle systems engineer agent</p>
		<h1 class="page-title">Ask the agent</h1>
		<p class="page-subtitle">
			A Gemini-capable engineering copilot with deterministic fallback and the same tools this platform uses (design space, evaluate,
			Pareto search, robust checks) &mdash; ask it questions in plain English instead of filling in
			forms. Each message is answered independently; it does not remember earlier messages in
			this transcript.
		</p>
	</header>

	<section class="panel">
		{#if agentExchanges.length > 0}
			<div class="chat-transcript">
				{#each agentExchanges as exchange}
					<div class="chat-row user">
						<div class="bubble bubble-user">{exchange.question}</div>
					</div>
					{#if exchange.error}
						<div class="chat-row agent">
							<div class="bubble bubble-error">{exchange.error}</div>
						</div>
					{:else if exchange.response}
						<div class="chat-row agent">
							<div class="bubble bubble-agent">
								<div class="markdown">{@html renderMarkdown(exchange.response.final_text)}</div>
								{#if exchange.response.tool_calls.length > 0}
									<details class="tool-calls">
										<summary
											>{exchange.response.tool_calls.length} tool call{exchange.response.tool_calls
												.length === 1
												? ''
												: 's'}{#if exchange.response.forced_final}
												&middot; hit max hops, answer was forced{/if}</summary
										>
										{#each exchange.response.tool_calls as call}
											<div class="tool-call">
												<code class:tool-error={call.is_error}>{call.name}</code>
												<pre>{JSON.stringify(call.input)}</pre>
											</div>
										{/each}
									</details>
								{/if}
							</div>
						</div>
					{:else}
						<div class="chat-row agent">
							<div class="bubble bubble-agent bubble-thinking">thinking&hellip;</div>
						</div>
					{/if}
				{/each}
			</div>
		{/if}

		<form
			class="chat-input"
			onsubmit={(e) => {
				e.preventDefault();
				askAgent();
			}}
		>
			<input
				type="text"
				placeholder="e.g. what's the cheapest design that still hits 300 miles of range?"
				bind:value={agentMessage}
				disabled={agentLoading}
			/>
			<button class="primary-btn" type="submit" disabled={agentLoading || !agentMessage.trim()}>
				{agentLoading ? 'asking…' : 'ask'}
			</button>
		</form>
		<p class="hint">
		Set <code>GEMINI_API_KEY</code> for Gemini narration. Without a key, the deterministic engineering
		fallback remains available; <code>ANTHROPIC_API_KEY</code> is still supported for the original tool agent.
		</p>
	</section>
</div>
