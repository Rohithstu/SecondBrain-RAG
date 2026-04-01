"""
SecondBrain Terminal Mode (Cycle 4)
Structured Answer Assembly - Zero Hallucination.
"""

import sys
import os
from sb_engine import SecondBrainEngine, start_monitoring # type: ignore
from dotenv import load_dotenv # type: ignore

# Load API Key for Terminal Mode
load_dotenv() 

# Force UTF-8 for Windows
try:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
except: pass

def main():
    print("=" * 80)
    print("  SecondBrain - Advanced Answer Assembly (Cycle 4)")
    print("=" * 80)

    engine = SecondBrainEngine()
    monitor = start_monitoring(engine)

    print("\n[!] Answer Assembly Layer is Active.")
    print("[!] Enter your question (or 'exit' to quit).")

    try:
        while True:
            try:
                print() # Ensure newline before prompt
                query = input("[?] Search: ").strip()
            except EOFError: break
            
            if not query or query.lower() in ["exit", "quit"]: break
            
            result = engine.search(query)
            
            print("-" * 80)
            if not result or "answer" not in result:
                print("  [!] No relevant answer found in documents.")
            else:
                v_icon = "✅ [VALIDATED]" if result.get("validation") else "❓ [UNVALIDATED]"
                print(f"  {v_icon} | Type: {result['type'].upper()} | Confidence: {result['confidence']:.2f}")
                print(f"  Source: {result['source']} ({result['sentence_count']} sentences used)")
                print(f"  {'.' * 60}")
                
                # Split and print the multi-line answer
                lines = result['answer'].split('\n')
                for l in lines:
                    safe_l = "".join(str(c) if ord(str(c)) < 128 else " " for c in l)
                    print(f"  • {safe_l}")
                
                print(f"  {'.' * 60}")
            print("-" * 80)
    finally:
        monitor.stop()
        monitor.join()

if __name__ == "__main__":
    main()
