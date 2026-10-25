import numpy as np
from django.test import SimpleTestCase, override_settings

from door.ai.pipeline import active_ai_backend, pipeline
from door.ai.recognizer import _opencv_embed_512
from door.ai.similarity import cosine


@override_settings(AI_BACKEND="mock")
class PipelineTests(SimpleTestCase):
    def test_same_input_same_embedding(self):
        a, b = pipeline.analyze(b"face-a"), pipeline.analyze(b"face-a")
        self.assertAlmostEqual(cosine(a.embedding, b.embedding), 1.0, places=4)

    def test_different_inputs_dissimilar(self):
        a, b = pipeline.analyze(b"face-a"), pipeline.analyze(b"face-b")
        self.assertLess(cosine(a.embedding, b.embedding), 0.3)

    def test_embedding_shape(self):
        self.assertEqual(pipeline.analyze(b"x").embedding.shape, (512,))

    @override_settings(AI_BACKEND="auto")
    def test_auto_backend_resolves_real_engine(self):
        self.assertIn(active_ai_backend(), ("insightface", "opencv"))

    def test_opencv_512_embedding_norm_and_stability(self):
        rng = np.random.default_rng(42)
        crop1 = rng.integers(30, 220, size=(120, 120, 3), dtype=np.uint8)
        emb1 = _opencv_embed_512(crop1)
        emb2 = _opencv_embed_512(crop1.copy())
        self.assertEqual(emb1.shape, (512,))
        self.assertAlmostEqual(float(np.linalg.norm(emb1)), 1.0, places=4)
        self.assertAlmostEqual(cosine(emb1, emb2), 1.0, places=5)
