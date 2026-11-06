"use strict";

function inspectAgent(frame, person) {
  const message = ([sender, recipient, channel, ballot]) => ({sender, recipient, channel, ballot});
  return {
    round: frame.round,
    received_reports: frame.delivered.filter(([, recipient]) => recipient === person).map(message),
    pending_outgoing_reports: frame.pending.filter(([sender]) => sender === person).map(message),
    voting_memory: frame.policy_memory[person],
    phase_memory: frame.phase_memory.filter(([id]) => id === person).map(([, phase, memory]) => ({phase, memory})),
    interventions: frame.interventions.filter(event => event.person === person),
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
