import math

import numpy as np
from PIL import Image
from keras.datasets import mnist
from keras.optimizers import SGD

from model import generator_model, discriminator_model, generator_containing_discriminator


def combine_images(generated_images):
    #生成图片拼接
    num = generated_images.shape[0]
    width = int(math.sqrt(num))
    height = int(math.ceil(float(num)/width))
    shape = generated_images.shape[1:3]
    image = np.zeros((height*shape[0], width*shape[1]),
                     dtype=generated_images.dtype)
    for index, img in enumerate(generated_images):
        i = int(index/width)
        j = index % width
        image[i*shape[0]:(i+1)*shape[0], j*shape[1]:(j+1)*shape[1]] = \
            img[:, :, 0]
    return image


def train(BATCH_SIZE):
    (X_train, y_train), (X_test, y_test) = mnist.load_data()
    # iamge_data_format选择"channels_last"或"channels_first"，该选项指定了Keras将要使用的维度顺序。
    # "channels_first"假定2D数据的维度顺序为(channels, rows, cols)，3D数据的维度顺序为(channels, conv_dim1, conv_dim2, conv_dim3)

    # 转换字段类型，并将数据导入变量中
    X_train = (X_train.astype(np.float32) - 127.5) / 127.5
    X_train = X_train[:, :, :, None]
    X_test = X_test[:, :, :, None]
    # X_train = X_train.reshape((X_train.shape, 1) + X_train.shape[1:])

    # 将定义好的模型架构赋值给特定的变量
    d = discriminator_model()
    g = generator_model()
    d_on_g = generator_containing_discriminator(g, d)

    # 定义生成器模型判别器模型更新所使用的优化算法及超参数
    d_optim = SGD(lr=0.001, momentum=0.9, nesterov=True)
    g_optim = SGD(lr=0.001, momentum=0.9, nesterov=True)

    # 编译三个神经网络并设置损失函数和优化算法，其中损失函数都是用的是二元分类交叉熵函数。编译是用来配置模型学习过程的
    g.compile(loss='binary_crossentropy', optimizer="SGD")
    d_on_g.compile(loss='binary_crossentropy', optimizer=g_optim)

    # 前一个架构在固定判别器的情况下训练了生成器，所以在训练判别器之前先要设定其为可训练。
    d.trainable = True
    d.compile(loss='binary_crossentropy', optimizer=d_optim)

    # 下面在满足epoch条件下进行训练
    for epoch in range(30):
        print("Epoch is", epoch)

        # 计算一个epoch所需要的迭代数量，即训练样本数除批量大小数的值取整；其中shape[0]就是读取矩阵第一维度的长度
        print("Number of batches", int(X_train.shape[0] / BATCH_SIZE))

        # 在一个epoch内进行迭代训练
        for index in range(int(X_train.shape[0] / BATCH_SIZE)):

            # 随机生成的噪声服从均匀分布，且采样下界为-1、采样上界为1，输出BATCH_SIZE×100个样本；即抽取一个批量的随机样本
            noise = np.random.uniform(-1, 1, size=(BATCH_SIZE, 100))

            # 抽取一个批量的真实图片
            image_batch = X_train[index * BATCH_SIZE:(index + 1) * BATCH_SIZE]

            # 生成的图片使用生成器对随机噪声进行推断；verbose为日志显示，0为不在标准输出流输出日志信息，1为输出进度条记录
            generated_images = g.predict(noise, verbose=0)

            # 每经过100次迭代输出一张生成的图片
            if index % 100 == 0:
                image = combine_images(generated_images)
                image = image * 127.5 + 127.5
                Image.fromarray(image.astype(np.uint8)).save(
                    "GAN/" + str(epoch) + "_" + str(index) + ".png")

            # 将真实的图片和生成的图片以多维数组的形式拼接在一起，真实图片在上，生成图片在下
            X = np.concatenate((image_batch, generated_images))

            # 生成图片真假标签，即一个包含两倍批量大小的列表；前一个批量大小都是1，代表真实图片，后一个批量大小都是0，代表伪造图片
            y = [1] * BATCH_SIZE + [0] * BATCH_SIZE

            # 判别器的损失；在一个batch的数据上进行一次参数更新
            d_loss = d.train_on_batch(X, y)
            print("batch %d d_loss : %f" % (index, d_loss))

            # 随机生成的噪声服从均匀分布
            noise = np.random.uniform(-1, 1, (BATCH_SIZE, 100))

            # 固定判别器
            d.trainable = False

            # 计算生成器损失；在一个batch的数据上进行一次参数更新
            g_loss = d_on_g.train_on_batch(noise, [1] * BATCH_SIZE)

            # 令判别器可训练
            d.trainable = True
            print("batch %d g_loss : %f" % (index, g_loss))

            # 每100次迭代保存一次生成器和判别器的权重
            if index % 100 == 9:
                g.save_weights('generator.weights', True)
                d.save_weights('discriminator.weights', True)


def test(BATCH_SIZE, nice=False):
    #训练完模型后，可以运行该函数生成图片
    g = generator_model()
    g.compile(loss='binary_crossentropy', optimizer="SGD")
    g.load_weights('generator.weights')
    if nice:
        d = discriminator_model()
        d.compile(loss='binary_crossentropy', optimizer="SGD")
        d.load_weights('discriminator.weights')
        noise = np.random.uniform(-1, 1, (BATCH_SIZE*20, 100))
        generated_images = g.predict(noise, verbose=1)
        d_pret = d.predict(generated_images, verbose=1)
        index = np.arange(0, BATCH_SIZE*20)
        index.resize((BATCH_SIZE*20, 1))
        pre_with_index = list(np.append(d_pret, index, axis=1))
        pre_with_index.sort(key=lambda x: x[0], reverse=True)
        nice_images = np.zeros((BATCH_SIZE,) + generated_images.shape[1:3], dtype=np.float32)
        nice_images = nice_images[:, :, :, None]
        for i in range(BATCH_SIZE):
            idx = int(pre_with_index[i][1])
            nice_images[i, :, :, 0] = generated_images[idx, :, :, 0]
        image = combine_images(nice_images)
    else:
        noise = np.random.uniform(-1, 1, (BATCH_SIZE, 100))
        generated_images = g.predict(noise, verbose=0)
        image = combine_images(generated_images)
    image = image*127.5+127.5
    Image.fromarray(image.astype(np.uint8)).save(
        "GAN/generated_image.png")


# train(132)
test(132)