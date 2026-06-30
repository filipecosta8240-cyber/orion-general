"""
Swarm Intelligence & Emergent Behavior
======================================
Enables swarm-like behaviors through stigmergy (indirect communication via
environment), flocking patterns, pheromone trails, and emergent collective
intelligence without central control.

Mechanisms:
- Stigmergy: Communication through shared memory (environment)
- Flocking: Local alignment with nearby agents
- Pheromone trails: Success paths left for others to follow
- Foraging: Distributed exploration and discovery
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
import threading


@dataclass
class Pheromone:
    """Represents a pheromone trail in the system."""
    pheromone_id: str
    location: str  # Concept, solution, or path
    intensity: float = 100.0  # 0-100, decays over time
    deposited_by: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    decay_rate: float = 0.95  # Decays 5% per period


@dataclass
class Stigmergy:
    """Indirect communication via shared environment."""
    location: str
    markers: Dict[str, int] = field(default_factory=dict)  # What agents have marked here
    pheromones: List[Pheromone] = field(default_factory=list)
    last_modified: datetime = field(default_factory=datetime.now)


class SwarmIntelligenceEngine:
    """
    Implements swarm intelligence patterns.
    
    Features:
    - Stigmergy (indirect communication)
    - Flocking (local alignment)
    - Pheromone trails (success marking)
    - Foraging (distributed discovery)
    - Emergent problem solving
    """
    
    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self.stigmergy_map: Dict[str, Stigmergy] = {}
        self.pheromones: Dict[str, Pheromone] = {}
        self.lock = threading.RLock()
        
        # Swarm parameters
        self.flocking_radius = 3  # How far agents look for alignment
        self.pheromone_diffusion_rate = 0.05  # Spread to neighbors
        self.pheromone_evaporation_rate = 0.03  # Evaporation per step
    
    def deposit_marker(self, location: str, agent_id: str, marker_type: str):
        """Agent leaves a marker (stigmergy communication)."""
        with self.lock:
            if location not in self.stigmergy_map:
                self.stigmergy_map[location] = Stigmergy(location=location)
            
            stigma = self.stigmergy_map[location]
            key = f"{agent_id}:{marker_type}"
            stigma.markers[key] = stigma.markers.get(key, 0) + 1
            stigma.last_modified = datetime.now()
    
    def deposit_pheromone(self, location: str, intensity: float, deposited_by: str):
        """
        Agent deposits pheromone trail (success marking).
        
        Args:
            location: Where the pheromone is deposited
            intensity: Initial intensity (0-100)
            deposited_by: Which agent deposited it
        """
        with self.lock:
            import uuid
            pheromone_id = str(uuid.uuid4())
            
            pheromone = Pheromone(
                pheromone_id=pheromone_id,
                location=location,
                intensity=min(100, intensity),
                deposited_by=deposited_by
            )
            
            self.pheromones[pheromone_id] = pheromone
            
            # Add to stigmergy location
            if location not in self.stigmergy_map:
                self.stigmergy_map[location] = Stigmergy(location=location)
            
            self.stigmergy_map[location].pheromones.append(pheromone)
            self.stigmergy_map[location].last_modified = datetime.now()
    
    def read_environment(self, location: str) -> Dict:
        """Agent reads what's in the environment at a location."""
        with self.lock:
            if location not in self.stigmergy_map:
                return {"markers": {}, "pheromones": []}
            
            stigma = self.stigmergy_map[location]
            
            # Collect pheromones with intensity > 0
            active_pheromones = [
                {
                    "from": p.deposited_by,
                    "intensity": p.intensity,
                    "age_seconds": (datetime.now() - p.timestamp).total_seconds()
                }
                for p in stigma.pheromones if p.intensity > 10
            ]
            
            return {
                "location": location,
                "markers": dict(stigma.markers),
                "pheromones": active_pheromones
            }
    
    def get_strongest_pheromone_direction(self, current_location: str, 
                                        nearby_locations: List[str]) -> Optional[str]:
        """
        Find direction with strongest pheromone trail (foraging).
        
        Returns:
            Next location to move toward, or None if no pheromones
        """
        with self.lock:
            best_location = None
            best_intensity = 0
            
            for location in nearby_locations:
                env = self.read_environment(location)
                max_intensity = max(
                    (p["intensity"] for p in env["pheromones"]),
                    default=0
                )
                
                if max_intensity > best_intensity:
                    best_intensity = max_intensity
                    best_location = location
            
            return best_location
    
    def update_pheromones(self):
        """
        Decay and diffuse pheromones (should be called periodically).
        Models pheromone evaporation and diffusion.
        """
        with self.lock:
            to_remove = []
            
            for pheromone_id, pheromone in self.pheromones.items():
                # Decay pheromone
                pheromone.intensity *= pheromone.decay_rate
                
                # Remove if too weak
                if pheromone.intensity < 1:
                    to_remove.append(pheromone_id)
            
            # Remove dead pheromones
            for pheromone_id in to_remove:
                del self.pheromones[pheromone_id]
    
    def get_swarm_status(self) -> Dict:
        """Get overview of swarm intelligence status."""
        with self.lock:
            active_pheromones = sum(1 for p in self.pheromones.values() if p.intensity > 10)
            total_markers = sum(len(s.markers) for s in self.stigmergy_map.values())
            
            # Find strongest pheromone trails
            top_trails = sorted(
                [(p.location, p.intensity, p.deposited_by) 
                 for p in self.pheromones.values() if p.intensity > 20],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                "total_locations": len(self.stigmergy_map),
                "active_pheromones": active_pheromones,
                "total_markers": total_markers,
                "top_trails": [
                    {"location": t[0], "intensity": t[1], "from": t[2]}
                    for t in top_trails
                ],
                "avg_pheromone_intensity": sum(p.intensity for p in self.pheromones.values()) / len(self.pheromones) if self.pheromones else 0
            }
    
    def get_emergent_solutions(self) -> List[Dict]:
        """Extract emergent solutions from pheromone patterns."""
        with self.lock:
            solutions = []
            
            # Locations with strong pheromone concentrations = good solutions
            location_intensities: Dict[str, float] = {}
            for pheromone in self.pheromones.values():
                if pheromone.intensity > 20:
                    location_intensities[pheromone.location] = \
                        location_intensities.get(pheromone.location, 0) + pheromone.intensity
            
            for location, intensity in sorted(location_intensities.items(),
                                             key=lambda x: x[1], reverse=True)[:5]:
                stigma = self.stigmergy_map.get(location)
                discovered_by = stigma.pheromones[0].deposited_by if stigma and stigma.pheromones else "unknown"
                solutions.append({
                    "solution": location,
                    "consensus_strength": min(100, intensity / 10),
                    "discovered_by": discovered_by,
                })
            
            return solutions
