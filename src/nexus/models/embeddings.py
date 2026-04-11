"""
Neural Embedding Fine-tuning with SimCSE

This module fine-tunes embeddings using SimCSE (Simple Contrastive Learning of
Sentence Embeddings) to create better representations of log messages.

Architecture:
- Base: sentence-transformers/all-mpnet-base-v2 (438M, 768-dim embeddings)
- Fine-tuning: SimCSE with hard negatives from incident logs
- Output: Optimized embeddings for anomaly detection

SimCSE works by:
- Positive pairs: same log sentence twice (with different dropout masks)
- Negative pairs: other logs from different incidents
- Loss: Contrastive loss with in-batch negatives

Applications:
- Better anomaly detection (autoencoder trained on improved embeddings)
- Improved log clustering
- More semantic log similarity comparisons
- Better retrieval for similar incidents

Usage:
    from nexus.models.embeddings import SimCSEEmbedder
    
    embedder = SimCSEEmbedder()
    embeddings = embedder.encode(["Log message 1", "Log message 2"])
"""

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
import torch
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer, util, losses
    from sentence_transformers.models import Transformer, Pooling
    _sentence_transformers_available = True
except ImportError:
    _sentence_transformers_available = False

logger = logging.getLogger(__name__)


class SimCSEEmbedder:
    """
    SimCSE-enhanced embedding model for log representation.
    
    Fine-tunes sentence embeddings on log data with contrastive learning.
    """
    
    BASE_MODEL = "sentence-transformers/all-mpnet-base-v2"
    EMBEDDING_DIM = 768
    
    def __init__(
        self,
        model_name: str = BASE_MODEL,
        device: Optional[torch.device] = None
    ):
        """
        Initialize embedder.
        
        Args:
            model_name: Pre-trained model name
            device: Torch device
        """
        if not _sentence_transformers_available:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self.device = device or torch.device("cpu")
        self.model_name = model_name
        
        # Load pre-trained model
        self.model = SentenceTransformer(model_name, device=str(self.device))
    
    def encode(
        self,
        sentences: List[str],
        batch_size: int = 128,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True
    ) -> np.ndarray:
        """
        Encode sentences to embeddings.
        
        Args:
            sentences: List of sentences to encode
            batch_size: Batch size for encoding
            show_progress_bar: Show progress bar
            convert_to_numpy: Convert output to numpy array
            
        Returns:
            Embeddings (N, 768)
        """
        embeddings = self.model.encode(
            sentences,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            convert_to_tensor=not convert_to_numpy,
            device=self.device
        )
        
        if convert_to_numpy and isinstance(embeddings, torch.Tensor):
            embeddings = embeddings.cpu().numpy()
        
        return embeddings
    
    def encode_single(self, sentence: str) -> np.ndarray:
        """Encode a single sentence."""
        return self.encode([sentence], batch_size=1)[0]
    
    def get_similarity(
        self,
        embeddings_a: np.ndarray,
        embeddings_b: np.ndarray,
        metric: str = "cosine"
    ) -> np.ndarray:
        """
        Compute similarity between embedding sets.
        
        Args:
            embeddings_a: Shape (N, 768)
            embeddings_b: Shape (M, 768)
            metric: "cosine" or "euclidean"
            
        Returns:
            Similarity matrix (N, M)
        """
        if isinstance(embeddings_a, np.ndarray):
            embeddings_a = torch.from_numpy(embeddings_a).to(self.device)
        if isinstance(embeddings_b, np.ndarray):
            embeddings_b = torch.from_numpy(embeddings_b).to(self.device)
        
        if metric == "cosine":
            similarities = util.cos_sim(embeddings_a, embeddings_b)
        elif metric == "euclidean":
            similarities = -torch.cdist(embeddings_a, embeddings_b, p=2.0)
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        return similarities.cpu().numpy()
    
    def get_most_similar(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray,
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Find most similar embeddings to query.
        
        Args:
            query_embedding: Single embedding (768,)
            corpus_embeddings: Corpus embeddings (N, 768)
            top_k: Number of results
            
        Returns:
            List of (index, similarity) tuples
        """
        # Reshape if needed
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        similarities = self.get_similarity(query_embedding, corpus_embeddings)[0]
        
        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = [(int(idx), float(similarities[idx])) for idx in top_indices]
        
        return results
    
    def save(self, save_path: str):
        """Save model."""
        self.model.save(save_path)
        logger.info(f"Saved model to {save_path}")
    
    @classmethod
    def load(cls, model_path: str, device: Optional[torch.device] = None) -> "SimCSEEmbedder":
        """Load model from disk."""
        device = device or torch.device("cpu")
        embedder = cls(device=device)
        embedder.model = SentenceTransformer(model_path, device=str(device))
        return embedder


class SimCSETrainer:
    """
    Trainer for SimCSE fine-tuning.
    
    Uses contrastive learning with:
    - In-batch negatives
    - Hard negatives from similar incidents
    - Dropout-based data augmentation for positive pairs
    """
    
    def __init__(
        self,
        base_model: str = "sentence-transformers/all-mpnet-base-v2",
        temperature: float = 0.05,
        device: Optional[torch.device] = None
    ):
        """Initialize trainer."""
        if not _sentence_transformers_available:
            raise ImportError("sentence-transformers not installed")
        
        self.device = device or torch.device("cpu")
        self.base_model = base_model
        self.temperature = temperature
        
        # Load base model
        word_embedding_model = Transformer(base_model)
        pooling_model = Pooling(
            word_embedding_model.get_word_embedding_dimension(),
            pooling_mode_mean_tokens=True
        )
        self.model = SentenceTransformer(modules=[word_embedding_model, pooling_model])
        self.model.to(self.device)
    
    def prepare_log_pairs(
        self,
        logs: List[str],
        incident_ids: List[str],
        hard_negatives: Optional[List[List[int]]] = None
    ) -> List[List[str]]:
        """
        Prepare training pairs: [anchor, positive, negative1, negative2, ...]
        
        Args:
            logs: List of log messages
            incident_ids: Incident ID for each log (for hard negatives)
            hard_negatives: Pre-computed hard negatives indices
            
        Returns:
            Triplet/quad lists for training
        """
        pairs = []
        
        for i, log in enumerate(logs):
            # Positive: same log (SimCSE uses dropout augmentation)
            positive = log
            
            # Negatives: logs from other incidents
            negatives = []
            for j, other_log in enumerate(logs):
                if i != j and incident_ids[i] != incident_ids[j]:
                    negatives.append(other_log)
            
            # Use hard negatives if provided
            if hard_negatives and i < len(hard_negatives):
                hard_neg_indices = hard_negatives[i]
                hard_negatives_list = [logs[idx] for idx in hard_neg_indices if idx < len(logs)]
                negatives = hard_negatives_list + negatives
            
            # Create training example: [anchor, positive, neg1, neg2, ...]
            if len(negatives) > 0:
                pair = [log, positive] + negatives[:3]  # Limit negatives
                pairs.append(pair)
        
        return pairs
    
    def train(
        self,
        logs: List[str],
        incident_ids: List[str],
        num_epochs: int = 3,
        batch_size: int = 32,
        warmup_steps: int = 100
    ) -> Dict:
        """
        Train model with contrastive learning.
        
        Args:
            logs: List of log messages
            incident_ids: Incident ID for each log
            num_epochs: Training epochs
            batch_size: Batch size
            warmup_steps: Learning rate warmup steps
            
        Returns:
            Training metrics
        """
        from sentence_transformers import InputExample
        from torch.utils.data import DataLoader
        
        logger.info(f"Training SimCSE on {len(logs)} logs...")
        
        # Prepare pairs
        pairs = self.prepare_log_pairs(logs, incident_ids)
        
        # Create training data
        train_examples = []
        for pair in pairs:
            if len(pair) >= 3:
                # Create examples with negatives
                train_examples.append(InputExample(texts=pair[:3]))
        
        # Create dataloader
        train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)
        
        # Setup loss
        train_loss = losses.CachedGIMMICKLoss(self.model, scale=20, similarity_fct=util.cos_sim)
        
        # Train
        self.model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=num_epochs,
            warmup_steps=warmup_steps,
            output_path=Path("./models/simcse_finetuned")
        )
        
        return {"epochs": num_epochs, "examples": len(train_examples)}
    
    def save(self, save_path: str):
        """Save trained model."""
        self.model.save(save_path)
        logger.info(f"Saved fine-tuned model to {save_path}")


class LogEmbeddingStore:
    """In-memory store of log embeddings with FAISS indexing."""
    
    def __init__(self, embedder: SimCSEEmbedder):
        """Initialize store."""
        self.embedder = embedder
        self.logs: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self.metadata: List[Dict] = []
        
        try:
            import faiss
            self.faiss = faiss
            self.index = None
        except ImportError:
            logger.warning("FAISS not available for fast retrieval")
            self.faiss = None
    
    def add_logs(
        self,
        logs: List[str],
        metadata: Optional[List[Dict]] = None
    ):
        """Add logs to store."""
        self.logs.extend(logs)
        
        # Encode
        new_embeddings = self.embedder.encode(logs, batch_size=128)
        
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
        
        # Store metadata
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{} for _ in logs])
        
        # Rebuild FAISS index if available
        if self.faiss and len(self.logs) > 0:
            self._build_faiss_index()
    
    def _build_faiss_index(self):
        """Build FAISS index for fast retrieval."""
        import faiss
        
        embeddings = np.asarray(self.embeddings, dtype=np.float32)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
    
    def search_similar(
        self,
        query_log: str,
        top_k: int = 10
    ) -> List[Tuple[str, float, Dict]]:
        """Search for similar logs."""
        query_embedding = self.embedder.encode_single(query_log).reshape(1, -1)
        
        if self.faiss and self.index:
            distances, indices = self.index.search(query_embedding, top_k)
            results = [
                (self.logs[int(idx)], float(dist), self.metadata[int(idx)])
                for dist, idx in zip(distances[0], indices[0])
                if idx < len(self.logs)
            ]
        else:
            # Fallback: brute force search
            results = self.embedder.get_most_similar(
                query_embedding[0],
                self.embeddings,
                top_k=top_k
            )
            results = [
                (self.logs[idx], sim, self.metadata[idx])
                for idx, sim in results
            ]
        
        return results
