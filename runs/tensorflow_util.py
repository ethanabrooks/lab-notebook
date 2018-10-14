# first party
from runs.run import Run
import tensorflow as tf


def summarize_run(run_path: str, summary_path: str):
    run = Run(run_path)
    summary_path = run.interpolate_keywords(summary_path)
    tb_writer = tf.summary.FileWriter(summary_path)
    run_string = tf.convert_to_tensor(run.pretty_print())
    tb_writer.add_summary(tf.Session().run(tf.summary.text(run_path, run_string)))
    tb_writer.flush()
    return summary_path
