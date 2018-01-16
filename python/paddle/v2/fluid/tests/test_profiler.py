import unittest
import os
import numpy as np
import paddle.v2.fluid as fluid
import paddle.v2.fluid.profiler as profiler
import paddle.v2.fluid.layers as layers
import paddle.v2.fluid.core as core


class TestProfiler(unittest.TestCase):
    def test_nvprof(self):
        if not fluid.core.is_compile_gpu():
            return
        epoc = 8
        dshape = [4, 3, 28, 28]
        data = layers.data(name='data', shape=[3, 28, 28], dtype='float32')
        conv = layers.conv2d(data, 20, 3, stride=[1, 1], padding=[1, 1])

        place = fluid.CUDAPlace(0)
        exe = fluid.Executor(place)
        exe.run(fluid.default_startup_program())

        output_file = 'cuda_profiler.txt'
        with profiler.cuda_profiler(output_file, 'csv') as nvprof:
            for i in range(epoc):
                input = np.random.random(dshape).astype('float32')
                exe.run(fluid.default_main_program(), feed={'data': input})
        os.remove(output_file)

    def test_profiler(self):
        image = fluid.layers.data(name='x', shape=[784], dtype='float32')
        hidden1 = fluid.layers.fc(input=image, size=128, act='relu')
        hidden2 = fluid.layers.fc(input=hidden1, size=64, act='relu')
        predict = fluid.layers.fc(input=hidden2, size=10, act='softmax')
        label = fluid.layers.data(name='y', shape=[1], dtype='int64')
        cost = fluid.layers.cross_entropy(input=predict, label=label)
        avg_cost = fluid.layers.mean(x=cost)
        optimizer = fluid.optimizer.Momentum(learning_rate=0.001, momentum=0.9)
        opts = optimizer.minimize(avg_cost)
        accuracy = fluid.evaluator.Accuracy(input=predict, label=label)

        states = ['CPU', 'GPU'] if core.is_compile_gpu() else ['CPU']
        for state in states:
            place = fluid.CPUPlace() if state == 'CPU' else fluid.CUDAPlace(0)
            exe = fluid.Executor(place)
            exe.run(fluid.default_startup_program())

            accuracy.reset(exe)

            with profiler.profiler(state, 'total') as prof:
                for iter in range(10):
                    if iter == 2:
                        profiler.reset_profiler()
                    x = np.random.random((32, 784)).astype("float32")
                    y = np.random.randint(0, 10, (32, 1)).astype("int64")

                    outs = exe.run(fluid.default_main_program(),
                                   feed={'x': x,
                                         'y': y},
                                   fetch_list=[avg_cost] + accuracy.metrics)
                    acc = np.array(outs[1])
                    pass_acc = accuracy.eval(exe)


if __name__ == '__main__':
    unittest.main()
