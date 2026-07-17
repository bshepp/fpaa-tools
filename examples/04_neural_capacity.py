#!/usr/bin/env python3
"""
Example 04: Neural Network Capacity Analysis

Analyzes what size neural networks can fit on your FPAA hardware.
No hardware connection required.

Usage:
    python3 04_neural_capacity.py
"""

import sys
sys.path.insert(0, '..')

from fpaa.neural import (
    estimate_network_capacity,
    create_perceptron,
    AnalogLayer,
    AnalogNeuron
)


def main():
    print("=" * 60)
    print("Analog Neural Network Capacity Analysis")
    print("OTC2310K04-PIKA: 4 × AN231E04 (80 CABs total)")
    print("=" * 60)
    
    # Basic capacity
    capacity = estimate_network_capacity(num_chips=4)
    
    print(f"\nHardware Resources:")
    print(f"   Total CABs: {capacity['total_cabs']}")
    print(f"   Max theoretical weights: ~{capacity['max_weights']}")
    
    print(f"\nNetwork Configurations That Fit:")
    
    # Small network
    small = capacity['small_network']
    status = "✓" if small['fits'] else "✗"
    print(f"\n   {status} {small['description']} Network:")
    print(f"      Weights: {small['weights']}")
    print(f"      Neurons: {small['neurons']}")
    print(f"      CABs needed: {small['cabs_needed']}")
    print(f"      Use case: XOR, simple classification")
    
    # Medium network
    medium = capacity['medium_network']
    status = "✓" if medium['fits'] else "✗"
    print(f"\n   {status} {medium['description']} Network:")
    print(f"      Weights: {medium['weights']}")
    print(f"      Neurons: {medium['neurons']}")
    print(f"      CABs needed: {medium['cabs_needed']}")
    print(f"      Use case: Simple patterns, audio features")
    
    # Single layer
    single = capacity['single_layer_max']
    print(f"\n   ✓ {single['description']} (Maximum single perceptron):")
    print(f"      Max inputs: {single['max_inputs']}")
    print(f"      Use case: Linear classifier, weighted sum")
    
    # Create example perceptron
    print(f"\n" + "=" * 60)
    print("Example: 4-Input Perceptron")
    print("=" * 60)
    
    neuron = create_perceptron(
        num_inputs=4,
        weights=[0.5, -0.3, 0.8, -0.1],
        bias=0.1,
        activation="relu"
    )
    
    print(f"\n   Inputs: {neuron.num_inputs}")
    print(f"   Bias: {neuron.bias}")
    print(f"   Activation: {neuron.activation}")
    print(f"   CABs required: {neuron.cabs_required}")
    
    print(f"\n   Weight mapping:")
    for i, w in enumerate(neuron.weights):
        caps = w.capacitor_ratio
        print(f"      w[{i}] = {w.value:+.2f} → Cin={caps[0]}, Cfb={caps[1]} → quantized={w.quantized_value}")
    
    # Multi-layer example
    print(f"\n" + "=" * 60)
    print("Example: 2-Layer Network (4-2-1)")
    print("=" * 60)
    
    # Hidden layer with 2 neurons
    hidden = AnalogLayer(layer_id=0)
    for n_id in range(2):
        neuron = create_perceptron(num_inputs=4, activation="relu")
        neuron.neuron_id = n_id
        hidden.add_neuron(neuron)
    
    # Output layer with 1 neuron
    output = AnalogLayer(layer_id=1)
    output_neuron = create_perceptron(num_inputs=2, activation="linear")
    output.add_neuron(output_neuron)
    
    print(f"\n   Hidden layer:")
    print(f"      Neurons: {hidden.num_neurons}")
    print(f"      CABs: {hidden.total_cabs}")
    print(f"      Chips needed: {hidden.chips_required}")
    
    print(f"\n   Output layer:")
    print(f"      Neurons: {output.num_neurons}")
    print(f"      CABs: {output.total_cabs}")
    
    total_cabs = hidden.total_cabs + output.total_cabs
    print(f"\n   Total network:")
    print(f"      CABs: {total_cabs}/80")
    print(f"      Utilization: {100*total_cabs/80:.1f}%")
    
    # Allocate to chips
    hidden.allocate_to_chips(4)
    output.allocate_to_chips(4)
    
    print(f"\n   Chip allocation:")
    print(f"      Hidden neurons → Chips: {hidden.chip_assignments}")
    print(f"      Output neurons → Chips: {output.chip_assignments}")
    
    print(f"\n" + "=" * 60)
    print("Precision Notes:")
    print("=" * 60)
    print("""
   • Weight precision: ~8 bits (capacitor matching ~0.1%)
   • Output precision: ~10 bits
   • Op-amp offset: ~1mV
   • Temperature drift: Consider calibration for precision apps
   • Best for: Real-time inference, low-latency, low-power
   • Not ideal for: Training (use digital, then deploy weights)
""")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

