import dependencies


def initialize_summarizer_model():
    try:
        # Smaller models that work reliably
        summarizer = dependencies.pipeline(
            "summarization", 
            model="sshleifer/distilbart-cnn-12-6",
            device=0 if dependencies.torch.cuda.is_available() else -1
        )

        print("✅ NLP SUMMARIZER loaded successfully")
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        # Fallback to lightweight models
        summarizer = None

    return summarizer

summarizer = initialize_summarizer_model()

def initialize_classifier_model():
    try:
        classifier = dependencies.pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=0 if dependencies.torch.cuda.is_available() else -1
        )

        print("✅ NLP CLASSIFIER loaded successfully")
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        # Fallback to lightweight models
        classifier = None

    return classifier

classifier = initialize_classifier_model()

def initialize_sentiment_model():
    try:
        sentiment = dependencies.pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=-1  # Use CPU (change to 0 for GPU if available)
        )
        
        print("✅ NLP SENTIMENT ANALYZER loaded successfully")
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        # Fallback to lightweight models
        sentiment = None

    return sentiment

sentiment_analyzer = initialize_sentiment_model()

def initialize_reply_generator():
    """Initialize the reply generation model with fallbacks"""
    try:
        # Try smaller, more available model first
        model_name = "gpt2"  # Base GPT-2 model that's widely available
        tokenizer = dependencies.AutoTokenizer.from_pretrained(model_name)
        model = dependencies.AutoModelForCausalLM.from_pretrained(model_name)
        
        # Configure padding for generation
        tokenizer.pad_token_id = tokenizer.eos_token_id
        
        print("✅ NLP REPLY GENERATOR loaded successfully")
        return dependencies.pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device=0 if dependencies.torch.cuda.is_available() else -1,
            framework="pt"
        )
        

    except Exception as e:
        print(f"⚠️ Could not load GPT model: {str(e)}")
        print("Falling back to simpler reply generation")
        return None

reply_generator = initialize_reply_generator()
