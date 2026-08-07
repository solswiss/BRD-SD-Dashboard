<script>
    let {obj, obj_of_inputs = $bindable(), default_value = obj.default, runSimulation } = $props();
</script>

<div class="input-container">
    <label for="{obj.py_name}">{obj.real_name} ({obj.units})</label>
    <div class="input">
        <input class="input-slider" type="range" name="{obj.py_name}" id="{obj.py_name}" min="{obj.min}" max="{obj.max}" step="{obj.step}" bind:value={obj_of_inputs} oninput={runSimulation}>
        <input class="input-number" type="number" name="{obj.py_name}" id="{obj.py_name}"  min="{obj.min}" max="{obj.max}" bind:value={obj_of_inputs} oninput={runSimulation}>
        <button onclick={()=>{obj_of_inputs=default_value;runSimulation();}}>⟳</button>
    </div>
</div>

<style>
.input-container {
    display: flex;
    flex-direction: column;
    align-items: start;
    padding: 4px 8px;
    color: #000;
    max-width: max(320px, 28%);

    label {
        word-break: break-all;
        font-size: .7rem;
    }
}
.input {
    display: flex;
    flex-grow: 1;
    align-items: center;
    justify-content: start;
    width: 100%;
    background: none;
    color: #000;
    height: 1.5rem; 
}
input, button {
    padding: 0;
    background: none;
    color: #000;
    border: 1px solid #e2e8f0; 
    height: 100%;
    max-height: 100%;
}

.input-slider {
    width: 100%;
    cursor: pointer;    
}
input[type="range"]::-webkit-slider-runnable-track, 
input[type="range"]::-moz-range-track {
    background: #000;
    border-radius: 0;
}
.input-number {
    height: 100%;
    width: 8ch;
    font-size: 14px;
}

button { 
    background: #fefefe; 
    border-radius: 0; 
    cursor: pointer; 
    font-size: 1rem; 
    padding: .3rem;
    transition: background 0.2s; 
}
button:hover:not(:disabled) { 
    background: #efefef; 
}
button:disabled { 
    background: #94a3b8; 
    cursor: not-allowed; 
}
</style>