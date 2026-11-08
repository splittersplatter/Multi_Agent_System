"use strict";

function inspectAgent(frame, person) {
  const received = frame.report_provenance?.delivered ?? frame.delivered.map(([sender, recipient, channel, ballot]) =>
    ({sender, recipient, channel, ballot, source_round: frame.round - 2, generated_round: frame.round - 1, delivered_round: frame.round}));
  const pending = frame.report_provenance?.pending ?? frame.pending.map(([sender, recipient, channel, ballot]) =>
    ({sender, recipient, channel, ballot, source_round: frame.round - 1, generated_round: frame.round, delivered_round: null}));
  return {
    round: frame.round,
    received_reports: received.filter(report => report.recipient === person),
    pending_outgoing_reports: pending.filter(report => report.sender === person),
    voting_memory: frame.policy_memory[person],
    phase_memory: frame.phase_memory.filter(([id]) => id === person).map(([, phase, memory]) => ({phase, memory})),
    interventions: frame.interventions.filter(event => event.person === person),
    ...(frame.deceptive_reports ? {researcher_deceptive_reports: frame.deceptive_reports.filter(event => event.sender === person)} : {}),
    ...(frame.preference_sight ? {researcher_preference_sight: frame.preference_sight.filter(event => event.observer === person)} : {}),
    ...(frame.overheard_reports ? {researcher_overheard_reports: frame.overheard_reports.filter(event => event.observer === person)} : {}),
    ...(frame.campaign_controller ? {researcher_campaign_edges: frame.campaign_controller.accepted.filter(([sender,recipient]) => sender === person || recipient === person)} : {}),
  };
}

// Researcher visualization only: reported or sensed votes are not preferences.
function estimatedPreferences(frame, observer) {
  const evidence = new Map();
  const add = (sender, ballot) => {
    if (sender === observer || !ballot.length) return;
    if (!evidence.has(sender)) evidence.set(sender, new Set());
    evidence.get(sender).add(ballot[0]);
  };
  for (const [sender, recipient, , ballot] of frame.delivered) if (recipient === observer) add(sender, ballot);
  for (const [recipient, sender, , , ballot] of frame.ballot_sensors) if (recipient === observer) add(sender, ballot);
  const result = new Map([[observer, frame.preferences[observer][0]]]);
  for (const [sender, choices] of evidence) if (choices.size === 1) result.set(sender, choices.values().next().value);
  return result;
}

if (typeof module !== "undefined" && module.exports) module.exports = {inspectAgent, estimatedPreferences};
