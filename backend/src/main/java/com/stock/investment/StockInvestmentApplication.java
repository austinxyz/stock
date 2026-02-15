package com.stock.investment;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class StockInvestmentApplication {

    public static void main(String[] args) {
        SpringApplication.run(StockInvestmentApplication.class, args);
    }
}
