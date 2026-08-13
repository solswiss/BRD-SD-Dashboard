<script>
    import { Slider } from "carbon-components-svelte";
    import Button from "$lib/components/button.svelte";
    import { Tooltip } from "bits-ui";
    import { HugeiconsIcon } from "@hugeicons/svelte";
    import { Information, InformationCircleIcon, Refresh01Icon, Reload } from "@hugeicons/core-free-icons";
    let {obj, obj_of_inputs = $bindable(), default_value = obj.default, func, resetInput } = $props();
    let labelText = $derived(`${obj.real_name} = ${obj_of_inputs.toFixed(2)}`)
</script>

<div class="input-container">
    <Slider onpointerup={func} fullWidth hideTextInput {labelText} name={obj.py_name} id={obj.py_name} min={obj.min} max={obj.max} step={obj.step} bind:value={obj_of_inputs}/>
    <div class="input-buttons-container">
        <Tooltip.Root>
            <Tooltip.Trigger>
                <Button variant="outline" size="icon-xs">
                    <HugeiconsIcon icon={Information} size={100}/>
                </Button>
            </Tooltip.Trigger>
            <Tooltip.Content>
                <div class="bg-bg">{obj.desc}</div>
            </Tooltip.Content>
        </Tooltip.Root>
        <Button variant="outline" size="icon-xs" onclick={()=>resetInput(obj.py_name,default_value)}>
            <HugeiconsIcon icon={Refresh01Icon}/>
        </Button>
    </div>
</div>

<style>
.input-container {
    position: relative;
    display: flex;
    flex-direction: row;
    align-items: start;
    color: #000;
    max-width: max(320px, 100%);
}
.input-buttons-container {
    position: absolute;
    top: 0;
    right: 0;
    display: grid;
    grid-auto-rows: 2;
}
</style>