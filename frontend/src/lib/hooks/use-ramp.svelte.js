export function useRamp({
	increment,
	maxFrequency = 200,
	minFrequency = 25,
	startDelay = 100,
	rampUpTime = 2500,
	canRamp
}) {
	let active = $state(false);
	let ramping = $state(false);
	let rampStartTimeout;
	let rampIntervalTimeout;
	let rampStartedAt;

	function rampUp() {
		if (!active) return;
		ramping = true;
		const timeSinceStart = Date.now() - (rampStartedAt ?? 0);
		const freq = rampUpTime === 0 ? 0 : Math.min(timeSinceStart, rampUpTime) / rampUpTime;
		if (!canRamp()) {
			reset();
			return;
		}
		increment();
		rampIntervalTimeout = setTimeout(
			() => rampUp(),
			maxFrequency - freq * (maxFrequency - minFrequency)
		);
	}

	function reset() {
		clearTimeout(rampStartTimeout);
		clearTimeout(rampIntervalTimeout);
		rampStartedAt = undefined;
		active = false;
		ramping = false;
	}

	function start() {
		active = true;
		rampStartedAt = Date.now();
		rampStartTimeout = setTimeout(() => rampUp(), startDelay);
	}

	return {
		start,
		reset,
		get active() {
			return active;
		},
		get ramping() {
			return ramping;
		}
	};
}