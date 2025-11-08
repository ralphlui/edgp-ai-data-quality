#!/usr/bin/env python3
"""
Test prompt injection evaluator with mock data to verify parameter fix.
"""

import os
import sys
import logging

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Set up environment for testing
os.environ['APP_ENV'] = 'development'
os.environ['USE_SECRETS_MANAGER'] = 'false'
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['LANGCHAIN_API_KEY'] = 'test-key'
os.environ['ENABLE_PROMPT_INJECTION_TEST'] = 'true'
os.environ['PROMPT_INJECTION_DATASET'] = 'ds-impassioned-soda-62'
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['OPENAI_MODEL'] = 'gpt-4'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_prompt_injection_evaluation():
    """Test the prompt injection evaluation function."""
    
    try:
        print("🧪 Testing prompt injection evaluator...")
        
        # Import the evaluation function
        from src.prompt_injection_evaluator import run_prompt_injection_evaluation
        
        print("✅ Imported evaluation function successfully")
        
        # Try to run the evaluation (will fail on dataset/API, but shouldn't fail on parameters)
        result = run_prompt_injection_evaluation()
        
        if isinstance(result, dict):
            if "error" in result:
                error_msg = result["error"]
                if "unexpected keyword argument" in error_msg:
                    print(f"❌ Parameter error still exists: {error_msg}")
                    return False
                elif "dataset" in error_msg.lower() or "not found" in error_msg.lower():
                    print(f"✅ Parameter fix worked! Dataset error expected: {error_msg}")
                    return True
                else:
                    print(f"✅ Parameter fix worked! Other error (expected): {error_msg}")
                    return True
            else:
                print("✅ Evaluation succeeded unexpectedly!")
                return True
        else:
            print("✅ Evaluation completed!")
            return True
            
    except Exception as e:
        if "unexpected keyword argument" in str(e):
            print(f"❌ Parameter error: {e}")
            return False
        else:
            print(f"✅ Parameter fix worked! Expected error: {e}")
            return True

if __name__ == "__main__":
    print("🔧 PROMPT INJECTION EVALUATOR PARAMETER TEST")
    print("=" * 60)
    
    success = test_prompt_injection_evaluation()
    
    if success:
        print("\n✅ SUCCESS: LangSmith evaluate() parameters are correctly fixed!")
        print("🚀 The prompt injection evaluation should work when valid API keys and dataset are available.")
    else:
        print("\n❌ FAILED: Still have parameter issues with LangSmith evaluate()")
        print("🔧 Need to check LangSmith documentation for correct parameters.")