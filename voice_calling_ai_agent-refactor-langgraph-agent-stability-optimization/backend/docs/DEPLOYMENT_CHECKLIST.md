# Deployment Checklist - LLM Optimizations

**Date**: 2026-02-27  
**Status**: Ready for Testing  

---

## Pre-Deployment Verification

### ✅ Code Changes Complete

- [x] Intent detection uses hardcoded Llama
- [x] Name enrichment uses hardcoded Llama
- [x] Slot extraction uses hardcoded Llama
- [x] Main agent uses hardcoded Moonshot
- [x] Conditional slot extraction implemented
- [x] Redundant extraction calls removed
- [x] Unused imports cleaned up
- [x] No diagnostics errors
- [x] Verification script passes (4/4)

### ✅ Documentation Complete

- [x] `OPTIMIZATION_COMPLETE_SUMMARY.md` - Overview
- [x] `REDUNDANT_SLOT_EXTRACTION_REMOVED.md` - Detailed changes
- [x] `LLM_CALLS_BEFORE_AFTER.md` - Visual comparison
- [x] `DEPLOYMENT_CHECKLIST.md` - This file
- [x] `verify_model_hardcoding.py` - Verification script

---

## Deployment Steps

### 1. Restart Backend Server

```bash
# Stop current server
pkill -f "python.*main.py"

# Or if using systemd
sudo systemctl restart twilio-ivr-backend

# Or if running manually
cd backend
source .venv/bin/activate
python main.py
```

### 2. Verify Server Started

```bash
# Check logs
tail -f backend/logs/application.log

# Look for:
# - "Application startup complete"
# - No errors during initialization
```

### 3. Test Basic Functionality

```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status": "healthy"}
```

---

## Post-Deployment Testing

### Test 1: Cancellation Flow (No Slot Extraction)

**Test Case**: User wants to cancel appointment

**Steps**:
1. Call the system
2. Say: "I need to cancel my appointment"
3. Follow the flow

**Expected in LangSmith**:
- ✅ Intent classification: `llama-3.1-8b-instant`
- ❌ NO slot extraction call
- ✅ Main agent: `moonshotai/kimi-k2-instruct-0905`
- ✅ Total: 2 LLM calls

**Expected Behavior**:
- System asks which appointment to cancel
- No unnecessary "time extraction" prompts in trace

---

### Test 2: Booking Flow (With Slot Extraction)

**Test Case**: User wants to book appointment

**Steps**:
1. Call the system
2. Say: "I want to book an appointment for tomorrow at 3 PM"
3. Follow the flow

**Expected in LangSmith**:
- ✅ Intent classification: `llama-3.1-8b-instant`
- ✅ Slot extraction (ONE call): `llama-3.1-8b-instant`
- ✅ Main agent: `moonshotai/kimi-k2-instruct-0905`
- ✅ Total: 3 LLM calls
- ❌ NO redundant extraction calls

**Expected Behavior**:
- Date and time extracted correctly
- No duplicate extraction prompts in trace

---

### Test 3: Rescheduling Flow (With Slot Extraction)

**Test Case**: User wants to reschedule appointment

**Steps**:
1. Call the system
2. Say: "I need to reschedule my appointment"
3. Provide new date/time when asked

**Expected in LangSmith**:
- ✅ Intent classification: `llama-3.1-8b-instant`
- ✅ Slot extraction (ONE call): `llama-3.1-8b-instant`
- ✅ Main agent: `moonshotai/kimi-k2-instruct-0905`
- ✅ Total: 3 LLM calls
- ❌ NO redundant "Extract the appointment time" calls

**Expected Behavior**:
- Appointment ID resolved correctly
- New date/time extracted correctly
- No duplicate extraction prompts

---

### Test 4: Multi-Turn Conversation (Loop-Back)

**Test Case**: Multiple back-and-forth turns

**Steps**:
1. Start booking flow
2. Provide information across multiple turns
3. Complete the booking

**Expected in LangSmith**:
- Turn 1: Full pipeline (intent + slot + agent)
- Turn 2+: Skip expensive nodes (user_context_loading, intent_guard, name_enrichment)
- Turn 2+: Only slot extraction + agent (if needed)

**Expected Behavior**:
- Faster responses on turns 2+
- No re-running of expensive nodes
- Conversation state preserved

---

## Monitoring Checklist

### LangSmith Traces

Check for these patterns:

#### ✅ Good Patterns
- Intent classification always uses `llama-3.1-8b-instant`
- Slot extraction (when it runs) uses `llama-3.1-8b-instant`
- Main agent always uses `moonshotai/kimi-k2-instruct-0905`
- Cancellation: 2 LLM calls per turn
- Booking/Rescheduling: 3 LLM calls per turn
- No duplicate extraction prompts

#### ❌ Bad Patterns (Report if seen)
- Slot extraction using Moonshot
- Slot extraction running for cancellation
- Multiple "Extract the appointment time" prompts
- More than 3 LLM calls per turn (booking/rescheduling)
- More than 2 LLM calls per turn (cancellation)

### Performance Metrics

Monitor these metrics:

| Metric | Before | Target After | Actual |
|--------|--------|--------------|--------|
| Avg response time (booking) | 2300ms | 800ms | ___ |
| Avg response time (cancellation) | 800ms | 600ms | ___ |
| LLM calls per turn (booking) | 6 | 3 | ___ |
| LLM calls per turn (cancellation) | 3 | 2 | ___ |
| API cost per turn | $0.000030 | $0.000015 | ___ |

### Error Monitoring

Watch for:
- [ ] No increase in error rates
- [ ] No new exceptions in logs
- [ ] No failed slot extractions
- [ ] No appointment matching failures

---

## Rollback Plan

If issues are detected:

### Quick Rollback (Git)

```bash
# Revert the changes
git revert HEAD~3  # Adjust number based on commits

# Restart server
sudo systemctl restart twilio-ivr-backend
```

### Manual Rollback

1. Restore old `tool_executor_node.py`:
   - Re-add `extract_slots_from_message` import
   - Restore redundant extraction calls
   - Remove `SLOT_REQUIRING_INTENTS` check

2. Restore old model selection:
   - Change `_get_model()` to use `create_llm_model(purpose=...)`
   - Remove `_get_agent_model()`

3. Restart server

---

## Success Criteria

### Must Have (Blocking)
- [x] Server starts without errors
- [ ] All test flows complete successfully
- [ ] No increase in error rates
- [ ] Correct models used (verified in LangSmith)

### Should Have (Monitor)
- [ ] 60-80% latency reduction observed
- [ ] 50% cost reduction observed
- [ ] No redundant LLM calls in traces
- [ ] User experience improved (faster responses)

### Nice to Have (Track)
- [ ] Positive user feedback
- [ ] Reduced API costs visible in billing
- [ ] Cleaner LangSmith traces

---

## Sign-Off

### Pre-Deployment
- [ ] Code reviewed
- [ ] Tests passing
- [ ] Documentation complete
- [ ] Rollback plan ready

### Post-Deployment
- [ ] Server restarted successfully
- [ ] Basic tests passing
- [ ] LangSmith traces verified
- [ ] Performance metrics improved
- [ ] No errors in logs

### Final Approval
- [ ] All success criteria met
- [ ] Team notified
- [ ] Monitoring in place
- [ ] Ready for production traffic

---

## Contact

If issues arise:
1. Check logs: `backend/logs/application.log`
2. Check LangSmith traces
3. Review this checklist
4. Execute rollback plan if needed

---

## Notes

- Expected deployment time: 5-10 minutes
- Expected testing time: 30-60 minutes
- Monitor for first 24 hours after deployment
- Review metrics after 1 week
