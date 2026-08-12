import { Context } from 'runed';

import { useRamp, } from '$lib/hooks/use-ramp.svelte';

export class NumberFieldRootContext {
	constructor( opts) {;this.opts = opts;}

	valid = $derived.by(() => {
		const value = this.opts.value.current;
		const min = this.opts.min?.current;
		const max = this.opts.max?.current;

		return (min === undefined || value >= min) && (max === undefined || value <= max);
	});
}

export class NumberFieldInputContext {
	constructor( rootState) {;this.rootState = rootState;}

	oninput = (e) => {
		const value = e.currentTarget.value;

		if (
			this.rootState.opts.min?.current !== undefined &&
			Number(value) < this.rootState.opts.min.current
		) {
			this.rootState.opts.value.current = this.rootState.opts.min.current;
		}
		if (
			this.rootState.opts.max?.current !== undefined &&
			Number(value) > this.rootState.opts.max.current
		) {
			this.rootState.opts.value.current = this.rootState.opts.max.current;
		}
	};

	props = $derived.by(() => ({
		type: 'number',
		oninput: this.oninput,
		min: this.rootState.opts.min?.current,
		max: this.rootState.opts.max?.current,
		'aria-invalid': !this.rootState.valid,
		step: this.rootState.opts.step.current
	}));
}

export class NumberFieldButton {
	rampState;
	constructor(
		 rootState,
		 opts
	) {;this.rootState = rootState;this.opts = opts;
		this.increment = this.increment.bind(this);
		this.rampState = useRamp({
			increment: () => this.increment(),
			canRamp: () => this.enabled,
			...this.rootState.opts.rampSettings.current
		});
	}

	onpointerdown(e) {
		this.increment();

		this.rampState.start();

		this.opts.onpointerdown.current?.(e);
	}

	onpointerup(e) {
		this.rampState.reset();
		this.opts.onpointerup.current?.(e);
	}

	onpointerleave(e) {
		this.rampState.reset();
		this.opts.onpointerleave.current?.(e);
	}

	onpointercancel(e) {
		this.rampState.reset();
		this.opts.onpointercancel.current?.(e);
	}

	onclick(e) {
		if (!this.rampState.ramping) return;

		this.increment();

		this.opts.onclick.current?.(e);
	}

	increment() {
		const step =
			this.opts.direction === 'up'
				? this.rootState.opts.step.current
				: -this.rootState.opts.step.current;
		this.rootState.opts.value.current += step;
	}

	enabled = $derived.by(() => {
		const step =
			this.opts.direction === 'up'
				? this.rootState.opts.step.current
				: -this.rootState.opts.step.current;

		const newValue = this.rootState.opts.value.current + step;

		if (
			this.rootState.opts.min?.current !== undefined &&
			newValue < this.rootState.opts.min.current
		) {
			return false;
		}

		if (
			this.rootState.opts.max?.current !== undefined &&
			newValue > this.rootState.opts.max.current
		) {
			return false;
		}

		return true;
	});

	props = $derived.by(() => ({
		disabled: !this.enabled || this.opts.disabled.current,
		onpointerdown: this.onpointerdown.bind(this),
		onpointerup: this.onpointerup.bind(this),
		onpointerleave: this.onpointerleave.bind(this),
		onpointercancel: this.onpointercancel.bind(this),
		onclick: this.onclick.bind(this)
	}));

	destroy() {
		this.rampState.reset();
	}
}

const ctx = new Context('number-field-root');

export function useNumberField(props) {
	return ctx.set(new NumberFieldRootContext(props));
}

export function useNumberFieldInput() {
	return new NumberFieldInputContext(ctx.get());
}

export function useNumberFieldButton(props) {
	return new NumberFieldButton(ctx.get(), props);
}