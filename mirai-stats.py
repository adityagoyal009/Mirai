#!/usr/bin/env python3
"""Quick stats viewer for Mirai analytics."""
import sys
sys.path.insert(0, '.')
from subconscious.swarm.services.analytics import Analytics

a = Analytics()
s = a.summary()

print("═══ MIRAI ANALYTICS ═══")
print(f"Total events:           {s['total_events']}")
print(f"WebSocket connections:  {s['total_connections']}")
print(f"Analyses started:       {s['total_analyses_started']}")
print(f"Analyses completed:     {s['total_analyses_completed']}")
print(f"PDF uploads:            {s['total_pdf_uploads']}")
print(f"PDF exports:            {s['total_pdf_exports']}")
print(f"Avg score:              {s['avg_score']}/10")
print(f"Avg duration:           {s['avg_duration_s']}s")
print(f"Companies analyzed:     {', '.join(s['companies_analyzed']) or 'None yet'}")
print(f"Verdict distribution:   {s['verdict_distribution'] or 'None yet'}")
