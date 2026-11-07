#include <stdio.h>
// teste com varias construcoes

int soma(int a, int b) {
    return a + b * 2;
}

int main() {
    int x = 5, y = 3;
    int v[3] = {1, 2, 3};
    float media = 2.5;
    x += 1;
    x++;
    for (int i = 0; i < 3; i++) {
        y = y + i;
    }
    if (x > 2 && y < 10) {
        x = soma(x, y);
    } else {
        x = 0;
    }
    while (x > 0) {
        x--;
    }
    printf("fim %d", x);
    return 0;
}