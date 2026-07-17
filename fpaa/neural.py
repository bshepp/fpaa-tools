"""
Analog Neural Network Primitives

Maps neural network concepts to FPAA hardware:
- Weights → Multiplier CAM capacitor ratios
- Summation → SumInv CAM
- Bias → GainInv offset
- Activation → Comparator or diode circuits
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass, field
import math


@dataclass
class AnalogWeight:
    """
    Represents a synaptic weight implemented in analog.
    
    In the AN231E04, weights are implemented using switched-capacitor
    multipliers. The weight value is determined by capacitor ratios,
    giving approximately 8-bit precision.
    """
    value: float  # Normalized weight value (-1.0 to 1.0)
    cab_id: int   # Which CAB implements this weight
    input_pin: Optional[int] = None  # Input I/O cell
    
    @property
    def quantized_value(self) -> int:
        """Return 8-bit quantized value (0-255)."""
        # Map -1..1 to 0..255
        normalized = (self.value + 1.0) / 2.0
        return max(0, min(255, int(normalized * 255)))
    
    @property
    def capacitor_ratio(self) -> Tuple[int, int]:
        """
        Return capacitor ratio for switched-cap implementation.
        
        Returns (input_caps, feedback_caps) where weight = input/feedback
        Maximum ratio is ~127:1 for 8-bit precision.
        """
        abs_weight = abs(self.value)
        
        if abs_weight < 0.01:
            return (0, 64)  # Near-zero weight
        elif abs_weight >= 1.0:
            return (64, 64)  # Unity gain
        else:
            # Find best integer ratio
            feedback = 64  # Fixed feedback capacitance
            input_caps = int(abs_weight * feedback)
            return (max(1, input_caps), feedback)


@dataclass
class AnalogNeuron:
    """
    A single analog neuron implemented on FPAA(s).
    
    Implements: y = activation(Σ(w_i × x_i) + bias)
    
    Hardware mapping:
    - Each weight: 1 Multiplier CAM (2 CABs each)
    - Summation: 1-2 SumInv CAMs
    - Bias: 1 GainInv CAM
    - Activation: 1-2 CABs (comparator + switches for ReLU)
    
    With 20 CABs per chip and ~2.5 CABs per weight:
    - ~6-8 inputs per chip (including activation)
    - 4 chips = ~24-32 total inputs possible
    """
    neuron_id: int
    weights: List[AnalogWeight] = field(default_factory=list)
    bias: float = 0.0
    activation: str = "relu"  # "relu", "sigmoid", "linear", "tanh"
    
    # Hardware allocation
    chip_id: Optional[int] = None
    start_cab: Optional[int] = None
    
    def add_input(self, weight: float, cab_id: int, input_pin: Optional[int] = None) -> None:
        """Add a weighted input to this neuron."""
        self.weights.append(AnalogWeight(
            value=weight,
            cab_id=cab_id,
            input_pin=input_pin
        ))
    
    @property
    def num_inputs(self) -> int:
        return len(self.weights)
    
    @property
    def cabs_required(self) -> int:
        """Estimate CABs needed for this neuron."""
        # Multiplier: ~2 CABs per weight
        weight_cabs = self.num_inputs * 2
        # Summer: 1-2 CABs depending on number of inputs
        summer_cabs = 1 if self.num_inputs <= 4 else 2
        # Bias: 1 CAB
        bias_cabs = 1
        # Activation: 1-2 CABs
        activation_cabs = 2 if self.activation in ["sigmoid", "tanh"] else 1
        
        return weight_cabs + summer_cabs + bias_cabs + activation_cabs
    
    def quantize_weights(self, bits: int = 8) -> List[int]:
        """Return all weights quantized to specified bit depth."""
        scale = (2 ** bits) - 1
        return [
            max(0, min(scale, int((w.value + 1.0) / 2.0 * scale)))
            for w in self.weights
        ]


@dataclass  
class AnalogLayer:
    """
    A layer of analog neurons.
    
    For multi-layer networks, outputs from one layer are routed
    to inputs of the next via I/O cells or direct CAB-to-CAB connections.
    """
    layer_id: int
    neurons: List[AnalogNeuron] = field(default_factory=list)
    
    # Hardware allocation across chips
    chip_assignments: List[int] = field(default_factory=list)
    
    @property
    def num_neurons(self) -> int:
        return len(self.neurons)
    
    @property
    def total_cabs(self) -> int:
        return sum(n.cabs_required for n in self.neurons)
    
    @property
    def chips_required(self) -> int:
        """Estimate chips needed (20 CABs per chip)."""
        return math.ceil(self.total_cabs / 20)
    
    def add_neuron(self, neuron: AnalogNeuron) -> None:
        """Add a neuron to this layer."""
        self.neurons.append(neuron)
    
    def allocate_to_chips(self, available_chips: int = 4) -> bool:
        """
        Allocate neurons to available chips.
        
        Returns True if allocation successful.
        """
        if self.chips_required > available_chips:
            return False
        
        cabs_per_chip = [0] * available_chips
        self.chip_assignments = []
        
        for neuron in self.neurons:
            # Find chip with most room
            for chip_id in range(available_chips):
                if cabs_per_chip[chip_id] + neuron.cabs_required <= 20:
                    neuron.chip_id = chip_id + 1
                    neuron.start_cab = cabs_per_chip[chip_id]
                    cabs_per_chip[chip_id] += neuron.cabs_required
                    self.chip_assignments.append(chip_id + 1)
                    break
            else:
                return False  # Couldn't fit neuron
        
        return True


def create_perceptron(
    num_inputs: int,
    weights: Optional[List[float]] = None,
    bias: float = 0.0,
    activation: str = "relu"
) -> AnalogNeuron:
    """
    Create a simple perceptron (single neuron).
    
    Args:
        num_inputs: Number of input connections
        weights: Optional weight values (random if not provided)
        bias: Bias value
        activation: Activation function type
        
    Returns:
        Configured AnalogNeuron
    """
    import random
    
    if weights is None:
        # Xavier-like initialization
        scale = 1.0 / math.sqrt(num_inputs)
        weights = [random.uniform(-scale, scale) for _ in range(num_inputs)]
    
    neuron = AnalogNeuron(
        neuron_id=0,
        bias=bias,
        activation=activation
    )
    
    for i, w in enumerate(weights):
        neuron.add_input(
            weight=w,
            cab_id=i * 2,  # Each weight uses 2 CABs
            input_pin=i % 4  # Map to I/O cells (4 per chip)
        )
    
    return neuron


def estimate_network_capacity(
    num_chips: int = 4,
    cabs_per_chip: int = 20
) -> dict:
    """
    Estimate network capacity for given hardware.
    
    Returns dict with estimates for different network configurations.
    """
    total_cabs = num_chips * cabs_per_chip
    
    # Assumptions:
    # - 2 CABs per weight (multiplier)
    # - 2 CABs for summer + activation per neuron
    cabs_per_weight = 2
    overhead_per_neuron = 4  # Summer + bias + activation
    
    return {
        "total_cabs": total_cabs,
        "max_weights": (total_cabs - 4) // cabs_per_weight,
        
        # Small network: 4 inputs, 2 hidden, 1 output
        "small_network": {
            "description": "4-2-1 (XOR capable)",
            "weights": 4*2 + 2*1,  # = 10
            "neurons": 3,
            "cabs_needed": 10*2 + 3*4,  # = 32
            "fits": 10*2 + 3*4 <= total_cabs
        },
        
        # Medium network: 4 inputs, 4 hidden, 2 output  
        "medium_network": {
            "description": "4-4-2",
            "weights": 4*4 + 4*2,  # = 24
            "neurons": 6,
            "cabs_needed": 24*2 + 6*4,  # = 72
            "fits": 24*2 + 6*4 <= total_cabs
        },
        
        # Single layer: maximize inputs to one output
        "single_layer_max": {
            "description": "N-1 perceptron",
            "max_inputs": (total_cabs - overhead_per_neuron) // cabs_per_weight,
            "neurons": 1
        }
    }

