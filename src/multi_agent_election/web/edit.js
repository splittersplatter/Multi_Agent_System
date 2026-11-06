"use strict";

// Compare JSON objects independently of key order; array order is meaningful.
function canonicalEditValue(value) {
  if (Array.isArray(value)) return value.map(canonicalEditValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonicalEditValue(value[key])]));
  }
  return value;
}
function sameEditValue(left, right) {
  return JSON.stringify(canonicalEditValue(left)) === JSON.stringify(canonicalEditValue(right));
}
function planAgentEdit(frame, person, values) {
  const changes = {};
  for (const key of ["preference", "group", "position", "overrides"]) {
    const previous = key === "preference" ? frame.preferences[person] :
      key === "group" ? frame.groups[person] : key === "position" ? frame.positions[person] : frame.overrides[person];
    if (!sameEditValue(values[key], previous)) changes[key] = values[key];
  }
  const oldNeighbors = frame.persistent_edges.filter(edge => edge[0] === person).map(edge => edge[1]);
  const oldCampaign = frame.campaign_edges.filter(edge => edge[0] === person).map(edge => edge[1]);
  const oldChannels = Object.keys(frame.private_channels).filter(name => frame.private_channels[name].includes(person));
  for (const [label, next, previous] of [["edges", values.neighbors, oldNeighbors], ["campaign_edges", values.campaignNeighbors, oldCampaign], ["channels", values.channels, oldChannels]]) {
    if (!Array.isArray(next) || next.some(item => typeof item !== "string") || new Set(next).size !== next.length) {
      throw new Error(`${label} must be a list of distinct IDs`);
    }
    const additions = next.filter(item => !previous.includes(item));
    const removals = previous.filter(item => !next.includes(item));
    if (additions.length) changes[`add_${label}`] = additions;
    if (removals.length) changes[`remove_${label}`] = removals;
  }
  if (values.ballot !== undefined) changes.ballot = values.ballot;
  return changes;
}

if (typeof module !== "undefined" && module.exports) module.exports = {planAgentEdit};
