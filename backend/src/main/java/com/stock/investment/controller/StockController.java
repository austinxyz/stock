package com.stock.investment.controller;

import com.stock.investment.dto.StockRequest;
import com.stock.investment.dto.StockResponse;
import com.stock.investment.service.StockService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/stocks")
@RequiredArgsConstructor
public class StockController {
    private final StockService stockService;

    @GetMapping
    public ResponseEntity<List<StockResponse>> getAllStocks() {
        return ResponseEntity.ok(stockService.getAllStocks());
    }

    @GetMapping("/{id}")
    public ResponseEntity<StockResponse> getStockById(@PathVariable Long id) {
        return ResponseEntity.ok(stockService.getStockById(id));
    }

    @GetMapping("/symbol/{symbol}")
    public ResponseEntity<StockResponse> getStockBySymbol(@PathVariable String symbol) {
        return ResponseEntity.ok(stockService.getStockBySymbol(symbol));
    }

    @GetMapping("/search")
    public ResponseEntity<List<StockResponse>> searchStocks(@RequestParam String keyword) {
        return ResponseEntity.ok(stockService.searchStocks(keyword));
    }

    @PostMapping
    public ResponseEntity<StockResponse> createStock(@RequestBody StockRequest request) {
        return ResponseEntity.ok(stockService.createStock(request));
    }

    @PostMapping("/import/{symbol}")
    public ResponseEntity<StockResponse> importStockFromYahoo(@PathVariable String symbol) {
        return ResponseEntity.ok(stockService.importStockFromYahoo(symbol));
    }

    @PutMapping("/{id}")
    public ResponseEntity<StockResponse> updateStock(
            @PathVariable Long id,
            @RequestBody StockRequest request) {
        return ResponseEntity.ok(stockService.updateStock(id, request));
    }

    @PutMapping("/price/{symbol}")
    public ResponseEntity<StockResponse> updateStockPrice(@PathVariable String symbol) {
        return ResponseEntity.ok(stockService.updateStockPrice(symbol));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteStock(@PathVariable Long id) {
        stockService.deleteStock(id);
        return ResponseEntity.ok().build();
    }
}
