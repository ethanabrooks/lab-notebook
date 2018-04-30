import tensorflow as tf

from runs.run import Run

def summarize_run(run_path: str, summary_path: str):
    tb_writer = tf.summary.FileWriter(summary_path)
    run_string = tf.convert_to_tensor(Run(run_path).pretty_print())
    tb_writer.add_summary(
        tf.Session().run(tf.summary.text(run_path, run_string)))
    tb_writer.flush()
