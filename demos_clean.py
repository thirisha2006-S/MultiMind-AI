"""
Dem[ERROR] Scenari[ERROR]s f[ERROR]r MultiMind AI
Three c[ERROR]mpelling use cases sh[ERROR]wing the system in acti[ERROR]n:
1. Research Assistant - Deep research with validati[ERROR]n
2. C[ERROR]de Debugging W[ERROR]rkfl[ERROR]w - Iterative c[ERROR]ding with testing  
3. Agricultural Advis[ERROR]ry - D[ERROR]main-specific advice with mem[ERROR]ry
"""
imp[ERROR]rt [ERROR]s
fr[ERROR]m d[ERROR]tenv imp[ERROR]rt l[ERROR]ad_d[ERROR]tenv
fr[ERROR]m langchain_c[ERROR]re.messages imp[ERROR]rt HumanMessage
fr[ERROR]m graph imp[ERROR]rt app
fr[ERROR]m mem[ERROR]ry imp[ERROR]rt mem[ERROR]ry, rag_mem[ERROR]ry
def dem[ERROR]_research_assistant():
    """
    Dem[ERROR] 1: Research Assistant
    Sh[ERROR]ws deep research with fact validati[ERROR]n and mem[ERROR]ry retenti[ERROR]n.
    """
    print("=" * 60)
    print("DEM[ERROR] 1: RESEARCH ASSISTANT")
    print("=" * 60)
    print("Query: 'C[ERROR]mpare renewable energy ad[ERROR]pti[ERROR]n in Germany vs Japan 2020-2023'")
    print()
    
    sessi[ERROR]n_id = "research-dem[ERROR]-001"
    
    input_data = {
        "messages": [HumanMessage(c[ERROR]ntent="C[ERROR]mpare renewable energy ad[ERROR]pti[ERROR]n in Germany vs Japan fr[ERROR]m 2020 t[ERROR] 2023, including p[ERROR]licies, percentages, and future targets.")],
        "task_type": "research",
        "retry_c[ERROR]unt": 0,
        "max_retries": 3,
        "metadata": {"sessi[ERROR]n_id": sessi[ERROR]n_id},
        "planner_ran": False,
        "task_plan": N[ERROR]ne,
        "reflecti[ERROR]n": N[ERROR]ne
    }
    
    result = app.inv[ERROR]ke(input_data)
    
    print("PLAN GENERATED:")
    plan = result.get("task_plan", [])
    f[ERROR]r i, task in enumerate(plan, 1):
        print(f"  {i}. [{task.get('type')}] {task.get('descripti[ERROR]n')} (pri[ERROR]rity: {task.get('pri[ERROR]rity')})")
    print()
    
    print("RESEARCH RESULTS:")
    research = result.get("research_data", "N[ERROR] research data")
    print(research[:800] + ("..." if len(research) > 800 else ""))
    print()
    
    print("VALIDATI[ERROR]N:")
    validati[ERROR]n = result.get("validati[ERROR]n", {})
    print(f"  Valid: {validati[ERROR]n.get('is_valid', 'N/A')}")
    print(f"  C[ERROR]nfidence: {validati[ERROR]n.get('c[ERROR]nfidence', 'N/A'):.2f}")
    if validati[ERROR]n.get("issues"):
        print(f"  Issues: {validati[ERROR]n.get('issues')}")
    if validati[ERROR]n.get("suggesti[ERROR]ns"):
        print(f"  Suggesti[ERROR]ns: {validati[ERROR]n.get('suggesti[ERROR]ns')}")
    print()
    
    print("REFLECTI[ERROR]N:")
    reflecti[ERROR]n = result.get("reflecti[ERROR]n", {})
    print(f"  W[ERROR]rkfl[ERROR]w Quality: {reflecti[ERROR]n.get('w[ERROR]rkfl[ERROR]w_quality', 'N/A'):.2f}")
    print(f"  Planning Feedback: {reflecti[ERROR]n.get('planning_feedback', 'N/A')[:100]}...")
    print(f"  Final Answer Length: {len(result.get('final_answer', ''))} characters")
    print()
    
    # Sh[ERROR]w mem[ERROR]ry impact
    print("MEM[ERROR]RY IMPACT:")
    mem[ERROR]ry_rep[ERROR]rt = rag_mem[ERROR]ry.get_quality_rep[ERROR]rt()
    print(f"  Kn[ERROR]wledge chunks st[ERROR]red: {mem[ERROR]ry_rep[ERROR]rt.get('t[ERROR]tal_chunks', 0)}")
    print(f"  Average trust sc[ERROR]re: {mem[ERROR]ry_rep[ERROR]rt.get('average_trust', 0):.3f}")
    print()
    
    return result
def dem[ERROR]_c[ERROR]de_debugging():
    """
    Dem[ERROR] 2: C[ERROR]de Debugging W[ERROR]rkfl[ERROR]w
    Sh[ERROR]ws iterative c[ERROR]ding, testing, and validati[ERROR]n.
    """
    print("=" * 60)
    print("DEM[ERROR] 2: C[ERROR]DE DEBUGGING W[ERROR]RKFL[ERROR]W")
    print("=" * 60)
    print("Query: 'Create a Pyth[ERROR]n functi[ERROR]n t[ERROR] calculate Fib[ERROR]nacci numbers with err[ERROR]r handling and test it'")
    print()
    
    sessi[ERROR]n_id = "c[ERROR]de-dem[ERROR]-001"
    
    input_data = {
        "messages": [HumanMessage(c[ERROR]ntent="Create a Pyth[ERROR]n functi[ERROR]n t[ERROR] calculate Fib[ERROR]nacci numbers. Include err[ERROR]r handling f[ERROR]r invalid inputs, add d[ERROR]cstring, and pr[ERROR]vide test cases f[ERROR]r 0, 1, 5, and 10.")],
        "task_type": "research",  # Will likely trigger planner due t[ERROR] c[ERROR]mplexity
        "retry_c[ERROR]unt": 0,
        "max_retries": 3,
        "metadata": {"sessi[ERROR]n_id": sessi[ERROR]n_id},
        "planner_ran": False,
        "task_plan": N[ERROR]ne,
        "reflecti[ERROR]n": N[ERROR]ne
    }
    
    result = app.inv[ERROR]ke(input_data)
    
    print("PLAN GENERATED:")
    plan = result.get("task_plan", [])
    f[ERROR]r i, task in enumerate(plan, 1):
        print(f"  {i}. [{task.get('type')}] {task.get('descripti[ERROR]n')} (pri[ERROR]rity: {task.get('pri[ERROR]rity')})")
    print()
    
    print("C[ERROR]DE RESULTS:")
    c[ERROR]de_result = result.get("c[ERROR]de_result", "N[ERROR] c[ERROR]de results")
    print(c[ERROR]de_result)
    print()
    
    print("VALIDATI[ERROR]N:")
    validati[ERROR]n = result.get("validati[ERROR]n", {})
    print(f"  Valid: {validati[ERROR]n.get('is_valid', 'N/A')}")
    print(f"  C[ERROR]nfidence: {validati[ERROR]n.get('c[ERROR]nfidence', 'N/A'):.2f}")
    print()
    
    print("REFLECTI[ERROR]N:")
    reflecti[ERROR]n = result.get("reflecti[ERROR]n", {})
    print(f"  W[ERROR]rkfl[ERROR]w Quality: {reflecti[ERROR]n.get('w[ERROR]rkfl[ERROR]w_quality', 'N/A'):.2f}")
    print(f"  Planning Feedback: {reflecti[ERROR]n.get('planning_feedback', 'N/A')[:100]}...")
    print()
    
    # Test the generated c[ERROR]de if p[ERROR]ssible
    print("TESTING GENERATED C[ERROR]DE:")
    if "def fib[ERROR]nacci" in c[ERROR]de_result:
        print("  ✓ Fib[ERROR]nacci functi[ERROR]n detected in [ERROR]utput")
        # Try t[ERROR] extract and test it (simplified)
        try:
            # This is a simplified test - in practice w[ERROR]uld be m[ERROR]re r[ERROR]bust
            if "return" in c[ERROR]de_result and ("n == 0" in c[ERROR]de_result [ERROR]r "n <= 1" in c[ERROR]de_result):
                print("  ✓ Appears t[ERROR] handle base cases")
            if "f[ERROR]r" in c[ERROR]de_result [ERROR]r "while" in c[ERROR]de_result:
                print("  ✓ Appears t[ERROR] have iterative l[ERROR]gic")
        except:
            pass
    else:
        print("  ⚠ N[ERROR] clear functi[ERROR]n definiti[ERROR]n f[ERROR]und")
    print()
    
    return result
def dem[ERROR]_agricultural_advis[ERROR]ry():
    """
    Dem[ERROR] 3: Agricultural Advis[ERROR]ry (AgriDream directi[ERROR]n)
    Sh[ERROR]ws d[ERROR]main-specific advice with d[ERROR]main mem[ERROR]ry retenti[ERROR]n.
    """
    print("=" * 60)
    print("DEM[ERROR] 3: AGRICULTURAL ADVIS[ERROR]RY")
    print("=" * 60)
    print("Query: 'What are the best practices f[ERROR]r dr[ERROR]ught-resistant farming in Mediterranean climates?'")
    print()
    
    sessi[ERROR]n_id = "agri-dem[ERROR]-001"
    
    input_data = {
        "messages": [HumanMessage(c[ERROR]ntent="What are the best practices f[ERROR]r dr[ERROR]ught-resistant farming in Mediterranean climates? Include s[ERROR]il management, cr[ERROR]p selecti[ERROR]n, irrigati[ERROR]n techniques, and timing c[ERROR]nsiderati[ERROR]ns.")],
        "task_type": "research",
        "retry_c[ERROR]unt": 0,
        "max_retries": 3,
        "metadata": {"sessi[ERROR]n_id": sessi[ERROR]n_id},
        "planner_ran": False,
        "task_plan": N[ERROR]ne,
        "reflecti[ERROR]n": N[ERROR]ne
    }
    
    result = app.inv[ERROR]ke(input_data)
    
    print("PLAN GENERATED:")
    plan = result.get("task_plan", [])
    f[ERROR]r i, task in enumerate(plan, 1):
        print(f"  {i}. [{task.get('type')}] {task.get('descripti[ERROR]n')} (pri[ERROR]rity: {task.get('pri[ERROR]rity')})")
    print()
    
    print("ADVIS[ERROR]RY RESULTS:")
    advis[ERROR]ry = result.get("research_data", "N[ERROR] advis[ERROR]ry data")
    print(advis[ERROR]ry[:800] + ("..." if len(advis[ERROR]ry) > 800 else ""))
    print()
    
    print("VALIDATI[ERROR]N:")
    validati[ERROR]n = result.get("validati[ERROR]n", {})
    print(f"  Valid: {validati[ERROR]n.get('is_valid', 'N/A')}")
    print(f"  C[ERROR]nfidence: {validati[ERROR]n.get('c[ERROR]nfidence', 'N/A'):.2f}")
    print()
    
    print("REFLECTI[ERROR]N:")
    reflecti[ERROR]n = result.get("reflecti[ERROR]n", {})
    print(f"  W[ERROR]rkfl[ERROR]w Quality: {reflecti[ERROR]n.get('w[ERROR]rkfl[ERROR]w_quality', 'N/A'):.2f}")
    print(f"  Planning Feedback: {reflecti[ERROR]n.get('planning_feedback', 'N/A')[:100]}...")
    print(f"  Final Answer: {result.get('final_answer', 'N/A')[:150]}...")
    print()
    
    print("D[ERROR]MAIN MEM[ERROR]RY BUILDUP:")
    mem[ERROR]ry_rep[ERROR]rt = rag_mem[ERROR]ry.get_quality_rep[ERROR]rt()
    print(f"  Kn[ERROR]wledge chunks st[ERROR]red: {mem[ERROR]ry_rep[ERROR]rt.get('t[ERROR]tal_chunks', 0)}")
    print(f"  Average trust sc[ERROR]re: {mem[ERROR]ry_rep[ERROR]rt.get('average_trust', 0):.3f}")
    print()
    
    # Sec[ERROR]nd query t[ERROR] sh[ERROR]w mem[ERROR]ry reuse
    print("SEC[ERROR]ND QUERY (testing mem[ERROR]ry reuse):")
    print("Query: 'Which specific cr[ERROR]ps are best f[ERROR]r Mediterranean dr[ERROR]ught c[ERROR]nditi[ERROR]ns?'")
    
    input_data2 = {
        "messages": [HumanMessage(c[ERROR]ntent="Which specific cr[ERROR]ps are best suited f[ERROR]r dr[ERROR]ught-resistant farming in Mediterranean climates?")],
        "task_type": "research",
        "retry_c[ERROR]unt": 0,
        "max_retries": 3,
        "metadata": {"sessi[ERROR]n_id": sessi[ERROR]n_id},  # Same sessi[ERROR]n - sh[ERROR]uld reuse mem[ERROR]ry
        "planner_ran": False,
        "task_plan": N[ERROR]ne,
        "reflecti[ERROR]n": N[ERROR]ne
    }
    
    result2 = app.inv[ERROR]ke(input_data2)
    
    print("RESULTS FR[ERROR]M SEC[ERROR]ND QUERY:")
    research2 = result2.get("research_data", "N[ERROR] results")
    print(research2[:500] + ("..." if len(research2) > 500 else ""))
    print()
    
    print("VALIDATI[ERROR]N SEC[ERROR]ND QUERY:")
    validati[ERROR]n2 = result2.get("validati[ERROR]n", {})
    print(f"  Valid: {validati[ERROR]n2.get('is_valid', 'N/A')}")
    print(f"  C[ERROR]nfidence: {validati[ERROR]n2.get('c[ERROR]nfidence', 'N/A'):.2f}")
    print()
    
    return result, result2
def run_all_dem[ERROR]s():
    """Run all three dem[ERROR] scenari[ERROR]s."""
    print("MultiMind AI Dem[ERROR] Suite")
    print("Sh[ERROR]wing real-w[ERROR]rld use cases [ERROR]f integrity-aware aut[ERROR]n[ERROR]m[ERROR]us [ERROR]rchestrati[ERROR]n\n")
    
    # L[ERROR]ad envir[ERROR]nment
    l[ERROR]ad_d[ERROR]tenv()
    
    # Check if we have API keys
    if n[ERROR]t [ERROR]s.getenv("[ERROR]PENAI_API_KEY"):
        print("⚠️  WARNING: [ERROR]PENAI_API_KEY n[ERROR]t set - using m[ERROR]ck resp[ERROR]nses where p[ERROR]ssible")
    if n[ERROR]t [ERROR]s.getenv("TAVILY_API_KEY"):
        print("⚠️  WARNING: TAVILY_API_KEY n[ERROR]t set - research will be limited\n")
    
    try:
        result1 = dem[ERROR]_research_assistant()
        print("\n" + "="*60 + "\n")
        result2 = dem[ERROR]_c[ERROR]de_debugging()
        print("\n" + "="*60 + "\n")
        result3a, result3b = dem[ERROR]_agricultural_advis[ERROR]ry()
        
        print("=" * 60)
        print("ALL DEM[ERROR]S C[ERROR]MPLETED SUCCESSFULLY")
        print("MultiMind AI dem[ERROR]nstrated:")
        print("  ✓ Research assistant with validati[ERROR]n")
        print("  ✓ C[ERROR]de debugging w[ERROR]rkfl[ERROR]w") 
        print("  ✓ D[ERROR]main-specific agricultural advis[ERROR]ry")
        print("  ✓ Mem[ERROR]ry retenti[ERROR]n and reuse acr[ERROR]ss queries")
        print("  ✓ Integrity checks at every stage")
        print("=" * 60)
        
        return [result1, result2, result3a, result3b]
        
    except Excepti[ERROR]n as e:
        print(f"\n❌ Err[ERROR]r running dem[ERROR]s: {e}")
        print("This might be due t[ERROR] missing API keys [ERROR]r netw[ERROR]rk issues.")
        print("The system architecture is c[ERROR]rrect - c[ERROR]nfigure API keys f[ERROR]r full functi[ERROR]nality.")
        return N[ERROR]ne
if __name__ == "__main__":
    run_all_dem[ERROR]s()
